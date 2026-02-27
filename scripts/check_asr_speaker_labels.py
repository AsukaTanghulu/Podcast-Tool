#!/usr/bin/env python3
"""
检查上游 ASR 说话人标注是否有效（独立脚本，不依赖 Web 流程）

本脚本严格按 Qwen.md 的官方调用链路：
1) Transcription.async_call(...)
2) Transcription.wait(task=task_id)
3) 从 transcription_url 下载 JSON 结果并解析 speaker_id

用法示例：
1) 本地音频：
   python scripts/check_asr_speaker_labels.py --audio-path data/audio/test.mp3

2) 远程音频 URL：
   python scripts/check_asr_speaker_labels.py --audio-url "https://example.com/test.mp3"

3) 自定义阈值：
   python scripts/check_asr_speaker_labels.py --audio-path data/audio/test.mp3 --min-non-null-rate 0.8 --min-speakers 2
"""

import argparse
import json
import os
import sys
from http import HTTPStatus
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import request


def _bootstrap_import_path() -> Path:
    project_root = Path(__file__).resolve().parents[1]
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    return project_root


def _normalize_speaker_id(raw: Optional[Any]) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if text.lower() in {"unknown", "none", "null", "nan"}:
        return None
    return text


def _analyze(paragraphs: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(paragraphs)
    normalized_ids: List[Optional[str]] = [_normalize_speaker_id(p.get("speaker_id")) for p in paragraphs]

    valid_ids = [sid for sid in normalized_ids if sid is not None]
    unknown_count = total - len(valid_ids)
    unique_speakers = sorted(set(valid_ids))

    switches = 0
    last_sid = None
    for sid in valid_ids:
        if last_sid is None:
            last_sid = sid
            continue
        if sid != last_sid:
            switches += 1
            last_sid = sid

    rate = (len(valid_ids) / total) if total > 0 else 0.0

    speaker_counter = Counter(valid_ids)

    return {
        "total_segments": total,
        "segments_with_valid_speaker_id": len(valid_ids),
        "segments_without_speaker_id": unknown_count,
        "valid_speaker_rate": rate,
        "unique_speaker_count": len(unique_speakers),
        "unique_speakers": unique_speakers,
        "speaker_switches": switches,
        "speaker_distribution": dict(speaker_counter),
    }


def _to_file_url(local_path: Path) -> str:
    return local_path.resolve().as_uri()


def _parse_language_hints(raw: Any) -> List[str]:
    if raw is None:
        return ["zh", "en"]
    if isinstance(raw, list):
        result = [str(x).strip() for x in raw if str(x).strip()]
        return result or ["zh", "en"]
    text = str(raw).strip()
    if not text:
        return ["zh", "en"]
    result = [part.strip() for part in text.split(",") if part.strip()]
    return result or ["zh", "en"]


def _extract_segments_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从 transcription_url 返回的 JSON 中提取 sentence 级 segment。"""
    segments: List[Dict[str, Any]] = []

    def consume_sentences(sentences: List[Dict[str, Any]]):
        for sentence in sentences:
            text = str(sentence.get("text", "")).strip()
            if not text:
                continue
            start = sentence.get("begin_time", 0)
            end = sentence.get("end_time", 0)
            try:
                start = float(start) / 1000.0
                end = float(end) / 1000.0
            except Exception:
                start = 0.0
                end = 0.0

            segments.append(
                {
                    "start": start,
                    "end": end,
                    "text": text,
                    "speaker_id": sentence.get("speaker_id"),
                }
            )

    if isinstance(payload.get("sentences"), list):
        consume_sentences(payload["sentences"])

    transcripts = payload.get("transcripts")
    if isinstance(transcripts, list):
        for transcript in transcripts:
            sentences = transcript.get("sentences") if isinstance(transcript, dict) else None
            if isinstance(sentences, list):
                consume_sentences(sentences)

    return segments


def _call_dashscope_asr(
    api_key: str,
    model: str,
    file_urls: List[str],
    language_hints: List[str],
    base_url: str,
    speaker_count: int,
) -> List[Dict[str, Any]]:
    import dashscope
    from dashscope.audio.asr import Transcription

    dashscope.api_key = api_key
    if base_url:
        dashscope.base_http_api_url = base_url

    call_kwargs = {
        "model": model,
        "file_urls": file_urls,
        "language_hints": language_hints,
        "diarization_enabled": True,
    }
    if speaker_count > 0:
        call_kwargs["speaker_count"] = speaker_count

    task_response = Transcription.async_call(**call_kwargs)

    if task_response.status_code != HTTPStatus.OK:
        message = getattr(task_response, "message", "")
        raise RuntimeError(f"提交任务失败: {task_response.status_code} - {message}")

    task_id = task_response.output["task_id"]
    transcription_response = Transcription.wait(task=task_id)

    output = transcription_response.output if hasattr(transcription_response, "output") else {}
    print("API 响应:", json.dumps(output, ensure_ascii=False))

    if transcription_response.status_code != HTTPStatus.OK:
        message = getattr(transcription_response, "message", "")
        raise RuntimeError(f"任务执行失败: {transcription_response.status_code} - {message}")

    all_segments: List[Dict[str, Any]] = []
    results = output.get("results", []) if isinstance(output, dict) else []
    for item in results:
        if not isinstance(item, dict):
            continue
        if item.get("subtask_status") != "SUCCEEDED":
            print("子任务失败:", json.dumps(item, ensure_ascii=False))
            continue

        url = item.get("transcription_url")
        if not url:
            continue

        payload = json.loads(request.urlopen(url).read().decode("utf-8"))
        all_segments.extend(_extract_segments_from_payload(payload))

    return all_segments


def main() -> int:
    parser = argparse.ArgumentParser(description="检查上游 ASR 说话人标注有效性")
    parser.add_argument("--audio-path", type=str, default="", help="本地音频路径")
    parser.add_argument("--audio-url", type=str, default="", help="远程音频 URL（可选，优先于本地路径）")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--model", type=str, default="", help="可选：覆盖模型名，如 paraformer-v2 / fun-asr")
    parser.add_argument("--base-url", type=str, default="", help="可选：DashScope API 地址，如 https://dashscope.aliyuncs.com/api/v1")
    parser.add_argument("--speaker-count", type=int, default=0, help="可选：说话人数（>0 时传给 ASR）")
    parser.add_argument("--min-non-null-rate", type=float, default=0.70, help="通过阈值：有效 speaker_id 占比，默认 0.70")
    parser.add_argument("--min-speakers", type=int, default=2, help="通过阈值：最少说话人数，默认 2")
    parser.add_argument("--report-path", type=str, default="", help="可选：输出 JSON 报告路径")

    args = parser.parse_args()

    if not args.audio_path and not args.audio_url:
        print("[错误] 至少需要提供 --audio-path 或 --audio-url 之一")
        return 2

    project_root = _bootstrap_import_path()

    try:
        from config import get_config
    except Exception as exc:
        print(f"[错误] 导入项目模块失败: {exc}")
        return 2

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = project_root / config_path

    if not config_path.exists():
        print(f"[错误] 配置文件不存在: {config_path}")
        return 2

    try:
        cfg = get_config(str(config_path))
    except Exception as exc:
        print(f"[错误] 读取配置失败: {exc}")
        return 2

    api_key = cfg.get("whisper.qwen_api_key") or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("[错误] 未找到 DASHSCOPE_API_KEY（配置和环境变量都为空）")
        return 2

    model = args.model.strip() or cfg.get("whisper.qwen_model", "paraformer-v2")
    language_hints = _parse_language_hints(cfg.get("whisper.language"))
    base_url = args.base_url.strip()

    audio_path = args.audio_path.strip()
    audio_url = args.audio_url.strip()

    file_urls: List[str] = []

    if audio_url:
        file_urls.append(audio_url)

    if audio_path and not audio_url:
        p = Path(audio_path)
        if not p.is_absolute():
            p = project_root / p
        if not p.exists():
            print(f"[错误] 本地音频不存在: {p}")
            return 2
        audio_path = str(p)
        file_urls.append(_to_file_url(p))

    print("=" * 72)
    print("ASR 说话人标注健康检查")
    print("=" * 72)
    print(f"模型: {model}")
    print(f"语言: {language_hints}")
    print(f"API Base URL: {base_url or '(SDK 默认)'}")
    print(f"本地音频: {audio_path or '(未提供)'}")
    print(f"远程音频 URL: {audio_url or '(未提供)'}")
    print(f"file_urls: {file_urls}")
    print(f"阈值: valid_speaker_rate >= {args.min_non_null_rate:.2f}, unique_speakers >= {args.min_speakers}")
    print("-" * 72)

    try:
        paragraphs = _call_dashscope_asr(
            api_key=api_key,
            model=model,
            file_urls=file_urls,
            language_hints=language_hints,
            base_url=base_url,
            speaker_count=args.speaker_count,
        )
    except Exception as exc:
        print(f"[错误] 转录失败: {exc}")
        return 2

    result = _analyze(paragraphs)

    passed = (
        result["total_segments"] > 0
        and result["valid_speaker_rate"] >= args.min_non_null_rate
        and result["unique_speaker_count"] >= args.min_speakers
    )

    print(f"总段落数: {result['total_segments']}")
    print(f"有效 speaker_id 段落: {result['segments_with_valid_speaker_id']}")
    print(f"无 speaker_id 段落: {result['segments_without_speaker_id']}")
    print(f"有效占比: {result['valid_speaker_rate']:.2%}")
    print(f"说话人数: {result['unique_speaker_count']} -> {result['unique_speakers']}")
    print(f"说话人切换次数(粗略): {result['speaker_switches']}")
    print(f"分布: {result['speaker_distribution']}")
    print("-" * 72)

    if passed:
        print("[通过] 上游 ASR 返回了有效说话人标注。")
    else:
        print("[未通过] 上游 ASR 说话人标注不足（可能大量为 null/unknown）。")
        if result["total_segments"] == 0:
            print("检测到 0 段落：更像是上游未产出可解析结果（可能 DECODE_ERROR 或输入不可访问）。")
            print("建议优先使用公网可访问的 https 音频 URL 进行核验。")
        print("建议排查：")
        print("1) 更换更清晰的双人对话音频（弱 BGM、少重叠）")
        print("2) 确认当前任务确实走了 diarization_enabled=True")
        print("3) 核对上游原始返回是否包含 speaker_id")

    report = {
        "passed": passed,
        "thresholds": {
            "min_non_null_rate": args.min_non_null_rate,
            "min_speakers": args.min_speakers,
        },
        "stats": result,
        "model": model,
        "language": language_hints,
        "base_url": base_url,
        "file_urls": file_urls,
        "audio_path": audio_path,
        "audio_url": audio_url,
    }

    if args.report_path:
        out = Path(args.report_path)
        if not out.is_absolute():
            out = project_root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"报告已写入: {out}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
