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

# 根据配置选择转录器
config_temp = get_config("config/config.yaml")
api_provider = config_temp.get("whisper.api_provider", "local")

if api_provider == "openai":
    from transcriber_api import WhisperAPITranscriber, TranscriptionError
    logger.info("使用 OpenAI Whisper API 模式")
elif api_provider == "qwen":
    from transcriber_qwen import QwenTranscriber, TranscriptionError
    logger.info("使用通义千问 API 模式")
else:
    from transcriber import transcribe_with_retry, TranscriptionError
    logger.info("使用本地 Whisper 模型")


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

        # 更新播客信息
        db.update_podcast(
            podcast_id,
            audio_url=metadata["audio_url"],
            duration=int(metadata["duration"]),
            file_size=metadata["file_size"],
            status="transcribing"
        )

        logger.info(f"✓ 音频获取成功: {audio_path}")

        # 3. 语音转录
        logger.info("=" * 50)
        logger.info("步骤 2/2: 语音转录")
        logger.info("=" * 50)

        api_provider = config.get("whisper.api_provider", "local")

        if api_provider == "openai":
            # 使用 OpenAI Whisper API
            transcriber_config = {
                "api_key": config.get("whisper.openai_api_key"),
                "language": config.get("whisper.language"),
                "paragraph_gap": config.get("analyzer.paragraph_gap")
            }
            transcriber = WhisperAPITranscriber(transcriber_config)
            paragraphs = transcriber.transcribe(audio_path)
            model_name = "openai-whisper-api"

        elif api_provider == "qwen":
            # 使用通义千问 API
            transcriber_config = {
                "api_key": config.get("whisper.qwen_api_key"),
                "language": config.get("whisper.language"),
                "model": config.get("whisper.qwen_model", "paraformer-v2"),
                "paragraph_gap": config.get("analyzer.paragraph_gap")
            }
            transcriber = QwenTranscriber(transcriber_config)
            paragraphs = transcriber.transcribe(audio_path, audio_url=metadata["audio_url"])
            model_name = f"qwen-{transcriber_config['model']}"

        else:
            # 使用本地模型
            transcriber_config = {
                "model_size": config.get("whisper.model_size"),
                "device": config.get("whisper.device"),
                "compute_type": config.get("whisper.compute_type"),
                "language": config.get("whisper.language"),
                "beam_size": config.get("whisper.beam_size"),
                "vad_filter": config.get("whisper.vad_filter"),
                "paragraph_gap": config.get("analyzer.paragraph_gap")
            }
            paragraphs = transcribe_with_retry(audio_path, transcriber_config)
            from transcriber import Transcriber
            transcriber = Transcriber(transcriber_config)
            model_name = config.get("whisper.model_size")

        # 生成 Markdown 和 PDF 格式
        logger.info("=" * 50)
        logger.info("生成转录文件")
        logger.info("=" * 50)

        from transcript_formatter import format_transcript

        # 生成 Markdown 文件
        transcript_filename = f"{podcast_id}.md"
        transcript_path = Path(config.get("storage.transcript_dir")) / transcript_filename

        format_transcript(
            paragraphs,
            metadata={
                "podcast_id": podcast_id,
                "model": model_name
            },
            output_format='markdown',
            output_path=str(transcript_path)
        )
        logger.info(f"✓ Markdown 文件: {transcript_path}")

        # 生成 PDF 文件（可选，需要 reportlab 库）
        try:
            pdf_path = str(transcript_path).replace('.md', '.pdf')
            format_transcript(
                paragraphs,
                metadata={
                    "podcast_id": podcast_id,
                    "model": model_name
                },
                output_format='pdf',
                output_path=pdf_path
            )
            logger.info(f"✓ PDF 文件: {pdf_path}")
        except ImportError:
            logger.warning("⚠ 未安装 reportlab，跳过 PDF 生成。安装方法: pip install reportlab")
        except Exception as e:
            logger.warning(f"⚠ PDF 生成失败: {e}")

        # 创建转录记录
        word_count = sum(len(p["text"]) for p in paragraphs)
        db.create_transcript(
            podcast_id,
            str(transcript_path),
            word_count=word_count,
            model_version=model_name
        )

        # 更新播客状态
        db.update_podcast(podcast_id, status="completed")

        logger.info(f"✓ 语音转录成功")
        logger.info(f"✓ 转录字数: {word_count}")

        # 4. 显示结果摘要
        logger.info("=" * 50)
        logger.info("处理完成")
        logger.info("=" * 50)
        logger.info(f"播客 ID: {podcast_id}")
        logger.info(f"音频文件: {audio_path}")
        logger.info(f"转录文件: {transcript_path}")
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
