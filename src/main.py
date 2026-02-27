"""
主程序入口
提供命令行界面进行播客分析
"""

import sys
import argparse
from pathlib import Path
from loguru import logger

# 配置环境变量（HuggingFace 镜像等）
from env_setup import *

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config
from database import get_db
from audio_fetcher import AudioFetcher, AudioFetchError, AudioQualityError
from transcriber_qwen import QwenTranscriber, TranscriptionError
from storage_manager import StorageManager

logger.info("使用通义千问 API 模式")


def setup_logging(config):
    """配置日志"""
    log_level = config.get("logging.level", "INFO")
    log_file = config.get("logging.file", "logs/app.log")

    # 确保日志目录存在
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # 配置 loguru
    logger.remove()  # 移除默认处理器
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )
    logger.add(
        log_file,
        level=log_level,
        rotation=config.get("logging.rotation", "10 MB"),
        retention=config.get("logging.retention", "7 days"),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
    )


def process_podcast(url: str, config, db):
    """
    处理播客的完整流程

    Args:
        url: 播客页面 URL
        config: 配置对象
        db: 数据库对象
    """
    logger.info(f"开始处理播客: {url}")

    # 1. 创建播客记录
    podcast_id = db.create_podcast(url)
    logger.info(f"创建播客记录: {podcast_id}")

    try:
        # 2. 音频获取
        logger.info("=" * 50)
        logger.info("步骤 1/2: 音频获取")
        logger.info("=" * 50)

        db.update_podcast(podcast_id, status="downloading")

        fetcher = AudioFetcher({
            "user_agent": config.get("download.user_agent"),
            "timeout": config.get("download.timeout"),
            "max_retries": config.get("download.max_retries"),
            "chunk_size": config.get("download.chunk_size")
        })

        audio_path, metadata = fetcher.fetch(
            url,
            save_dir=config.get("storage.audio_dir")
        )

        # 更新播客信息（包括音频文件路径）
        db.update_podcast(
            podcast_id,
            audio_url=metadata["audio_url"],
            duration=int(metadata["duration"]),
            file_size=metadata["file_size"],
            audio_file_path=audio_path,  # 保存音频文件路径
            status="transcribing"
        )

        logger.info(f"✓ 音频获取成功: {audio_path}")

        # 3. 语音转录（仅使用通义千问 API）
        logger.info("=" * 50)
        logger.info("步骤 2/2: 语音转录")
        logger.info("=" * 50)

        transcriber_config = {
            "api_key": config.get("whisper.qwen_api_key"),
            "language": config.get("whisper.language"),
            "model": config.get("whisper.qwen_model", "paraformer-v2"),
            "paragraph_gap": config.get("analyzer.paragraph_gap")
        }
        transcriber = QwenTranscriber(transcriber_config)
        paragraphs = transcriber.transcribe(audio_path, audio_url=metadata["audio_url"])
        model_name = f"qwen-{transcriber_config['model']}"

        # 获取播客信息（包含栏目）
        podcast = db.get_podcast(podcast_id)
        category = podcast.get('category', '') if podcast else ''

        # 初始化存储管理器
        storage = StorageManager(config)

        # 生成转录文件（JSON, Markdown, PDF）
        logger.info("=" * 50)
        logger.info("生成转录文件")
        logger.info("=" * 50)

        from transcript_formatter import format_transcript
        import json

        # 1. 保存 JSON 格式（用于 Web 界面对话式布局）
        transcript_json_path = storage.get_transcript_path(podcast_id, category, "json")
        storage.ensure_directory(transcript_json_path)

        json_data = {
            "segments": paragraphs,
            "metadata": {
                "podcast_id": podcast_id,
                "model": model_name,
                "category": category or "未分类",
                "speaker_names": {}  # 初始为空，用户可以通过 Web 界面重命名
            },
            "word_count": sum(len(p["text"]) for p in paragraphs),
            "paragraph_count": len(paragraphs)
        }

        with open(transcript_json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ JSON 文件: {transcript_json_path}")

        # 2. 生成 Markdown 文件
        transcript_md_path = storage.get_transcript_path(podcast_id, category, "md")
        storage.ensure_directory(transcript_md_path)

        format_transcript(
            paragraphs,
            metadata={
                "podcast_id": podcast_id,
                "model": model_name,
                "category": category or "未分类",
                "speaker_names": {}
            },
            output_format='markdown',
            output_path=str(transcript_md_path)
        )
        logger.info(f"✓ Markdown 文件: {transcript_md_path}")

        # 3. 生成 PDF 文件（可选，需要 reportlab 库）
        pdf_path = None
        try:
            transcript_pdf_path = storage.get_transcript_path(podcast_id, category, "pdf")
            storage.ensure_directory(transcript_pdf_path)

            format_transcript(
                paragraphs,
                metadata={
                    "podcast_id": podcast_id,
                    "model": model_name,
                    "category": category or "未分类"
                },
                output_format='pdf',
                output_path=str(transcript_pdf_path)
            )
            pdf_path = transcript_pdf_path
            logger.info(f"✓ PDF 文件: {transcript_pdf_path}")
        except ImportError:
            logger.warning("⚠ 未安装 reportlab，跳过 PDF 生成。安装方法: pip install reportlab")
        except Exception as e:
            logger.warning(f"⚠ PDF 生成失败: {e}")

        # 创建转录记录（保存 JSON 路径，用于 Web 界面）
        word_count = sum(len(p["text"]) for p in paragraphs)
        db.create_transcript(
            podcast_id,
            str(transcript_json_path),  # 保存 JSON 路径
            word_count=word_count,
            model_version=model_name
        )

        # 更新播客状态
        db.update_podcast(podcast_id, status="completed")

        logger.info(f"✓ 语音转录成功")
        logger.info(f"✓ 转录字数: {word_count}")
        if category:
            logger.info(f"✓ 栏目分类: {category}")

        # 4. 显示结果摘要
        logger.info("=" * 50)
        logger.info("处理完成")
        logger.info("=" * 50)
        logger.info(f"播客 ID: {podcast_id}")
        logger.info(f"栏目: {category or '未分类'}")
        logger.info(f"音频文件: {audio_path}")
        logger.info(f"Markdown 文件: {transcript_md_path}")
        if pdf_path:
            logger.info(f"PDF 文件: {pdf_path}")
        logger.info(f"段落数量: {len(paragraphs)}")
        logger.info(f"总字数: {word_count}")

        # 显示前 3 个段落预览
        logger.info("\n转录预览（前 3 段）:")
        formatted = transcriber.format_transcript_text(paragraphs[:3])
        print(formatted)

        return podcast_id

    except AudioFetchError as e:
        logger.error(f"✗ 音频获取失败: {e}")
        db.update_podcast(podcast_id, status="failed", error_message=str(e))
        raise

    except AudioQualityError as e:
        logger.error(f"✗ 音频质量不合格: {e}")
        db.update_podcast(podcast_id, status="failed", error_message=str(e))
        raise

    except TranscriptionError as e:
        logger.error(f"✗ 语音转录失败: {e}")
        db.update_podcast(podcast_id, status="failed", error_message=str(e))
        raise

    except Exception as e:
        logger.error(f"✗ 处理失败: {e}")
        db.update_podcast(podcast_id, status="failed", error_message=str(e))
        raise


def process_documentary(file_path: str, documentary_id: str, config, db):
    """
    处理纪录片的完整流程

    Args:
        file_path: 上传的文件路径
        documentary_id: 纪录片 ID
        config: 配置对象
        db: 数据库对象
    """
    logger.info(f"开始处理纪录片: {documentary_id}")

    try:
        # 1. 更新状态为转录中
        db.update_podcast(documentary_id, status="transcribing")

        # 2. 语音转录（使用通义千问 API）
        logger.info("=" * 50)
        logger.info("语音转录")
        logger.info("=" * 50)

        transcriber_config = {
            "api_key": config.get("whisper.qwen_api_key"),
            "language": config.get("whisper.language"),
            "model": config.get("whisper.qwen_model", "paraformer-v2"),
            "paragraph_gap": config.get("analyzer.paragraph_gap")
        }
        transcriber = QwenTranscriber(transcriber_config)

        # 对于本地文件，需要先上传到 OSS 或使用文件 URL
        # 这里我们直接传递本地文件路径，transcriber 会处理
        paragraphs = transcriber.transcribe(file_path)
        model_name = f"qwen-{transcriber_config['model']}"

        # 获取纪录片信息（包含栏目）
        documentary = db.get_podcast(documentary_id)
        category = documentary.get('category', '') if documentary else ''
        title = documentary.get('title', '未命名纪录片') if documentary else '未命名纪录片'

        # 初始化存储管理器
        storage = StorageManager(config)

        # 生成转录文件（JSON, Markdown, PDF）
        logger.info("=" * 50)
        logger.info("生成转录文件")
        logger.info("=" * 50)

        from transcript_formatter import format_transcript
        import json

        # 1. 保存 JSON 格式（用于 Web 界面对话式布局）
        transcript_json_path = storage.get_transcript_path(documentary_id, category, "json")
        storage.ensure_directory(transcript_json_path)

        json_data = {
            "segments": paragraphs,
            "metadata": {
                "podcast_id": documentary_id,
                "title": title,
                "model": model_name,
                "category": category or "未分类",
                "content_type": "documentary",
                "speaker_names": {}
            },
            "word_count": sum(len(p["text"]) for p in paragraphs),
            "paragraph_count": len(paragraphs)
        }

        with open(transcript_json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ JSON 文件: {transcript_json_path}")

        # 2. 生成 Markdown 文件
        transcript_md_path = storage.get_transcript_path(documentary_id, category, "md")
        storage.ensure_directory(transcript_md_path)

        format_transcript(
            paragraphs,
            metadata={
                "podcast_id": documentary_id,
                "title": title,
                "model": model_name,
                "category": category or "未分类",
                "content_type": "documentary",
                "speaker_names": {}
            },
            output_format='markdown',
            output_path=str(transcript_md_path)
        )
        logger.info(f"✓ Markdown 文件: {transcript_md_path}")

        # 3. 生成 PDF 文件（可选）
        pdf_path = None
        try:
            transcript_pdf_path = storage.get_transcript_path(documentary_id, category, "pdf")
            storage.ensure_directory(transcript_pdf_path)

            format_transcript(
                paragraphs,
                metadata={
                    "podcast_id": documentary_id,
                    "title": title,
                    "model": model_name,
                    "category": category or "未分类",
                    "content_type": "documentary"
                },
                output_format='pdf',
                output_path=str(transcript_pdf_path)
            )
            pdf_path = transcript_pdf_path
            logger.info(f"✓ PDF 文件: {transcript_pdf_path}")
        except ImportError:
            logger.warning("⚠ 未安装 reportlab，跳过 PDF 生成。安装方法: pip install reportlab")
        except Exception as e:
            logger.warning(f"⚠ PDF 生成失败: {e}")

        # 创建转录记录（保存 JSON 路径）
        word_count = sum(len(p["text"]) for p in paragraphs)
        db.create_transcript(
            documentary_id,
            str(transcript_json_path),  # 保存 JSON 路径
            word_count=word_count,
            model_version=model_name
        )

        # 更新纪录片状态
        db.update_podcast(
            documentary_id,
            status="completed",
            title=title
        )

        logger.info(f"✓ 语音转录成功")
        logger.info(f"✓ 转录字数: {word_count}")
        if category:
            logger.info(f"✓ 栏目分类: {category}")

        # 显示结果摘要
        logger.info("=" * 50)
        logger.info("处理完成")
        logger.info("=" * 50)
        logger.info(f"纪录片 ID: {documentary_id}")
        logger.info(f"标题: {title}")
        logger.info(f"栏目: {category or '未分类'}")
        logger.info(f"Markdown 文件: {transcript_md_path}")
        if pdf_path:
            logger.info(f"PDF 文件: {pdf_path}")
        logger.info(f"段落数量: {len(paragraphs)}")
        logger.info(f"总字数: {word_count}")

        return documentary_id

    except TranscriptionError as e:
        logger.error(f"✗ 语音转录失败: {e}")
        db.update_podcast(documentary_id, status="failed", error_message=str(e))
        raise

    except Exception as e:
        logger.error(f"✗ 处理失败: {e}")
        db.update_podcast(documentary_id, status="failed", error_message=str(e))
        raise


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="播客分析工具")
    parser.add_argument("url", help="小宇宙播客页面 URL")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径")

    args = parser.parse_args()

    # 加载配置
    config = get_config(args.config)
    setup_logging(config)

    logger.info(f"播客分析工具 v{config.get('app.version')}")

    # 初始化数据库
    db = get_db(config.get("database.path"))

    try:
        # 处理播客
        podcast_id = process_podcast(args.url, config, db)
        logger.info(f"\n✓ 全部完成！播客 ID: {podcast_id}")
        return 0

    except KeyboardInterrupt:
        logger.warning("\n用户中断")
        return 1

    except Exception as e:
        logger.error(f"\n✗ 处理失败: {e}")
        return 1

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
