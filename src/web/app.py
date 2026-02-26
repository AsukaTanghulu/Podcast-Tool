"""
Flask Web 应用
提供播客分析的 Web 界面
"""

from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_cors import CORS
from pathlib import Path
import sys
import markdown
import os

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config
from database import get_db
from loguru import logger
from utils.file_naming import sanitize_filename, rename_podcast_files, delete_podcast_files

# 创建 Flask 应用
app = Flask(__name__)
CORS(app)

# 加载配置（使用绝对路径）
config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
config = get_config(str(config_path))
app.config['SECRET_KEY'] = 'your-secret-key-here'  # 生产环境应使用环境变量

# 初始化数据库
db_path = Path(__file__).parent.parent.parent / config.get("database.path")
db = get_db(str(db_path))

# 基础目录配置
project_root = Path(__file__).parent.parent.parent
base_dirs = {
    'audio': project_root / config.get('storage.audio_dir'),
    'transcript': project_root / config.get('storage.transcript_dir'),
    'note': project_root / config.get('storage.note_dir')
}


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/podcasts', methods=['GET'])
def get_podcasts():
    """获取播客列表"""
    try:
        podcasts = db.get_all_podcasts()
        return jsonify({
            'success': True,
            'data': podcasts
        })
    except Exception as e:
        logger.error(f"获取播客列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/podcasts/<podcast_id>', methods=['GET'])
def get_podcast(podcast_id):
    """获取播客详情"""
    try:
        podcast = db.get_podcast(podcast_id)
        if not podcast:
            return jsonify({
                'success': False,
                'error': '播客不存在'
            }), 404

        # 获取转录记录
        transcripts = db.get_transcripts_by_podcast(podcast_id)

        # 获取笔记记录
        notes = db.get_notes_by_podcast(podcast_id)

        return jsonify({
            'success': True,
            'data': {
                'podcast': podcast,
                'transcripts': transcripts,
                'notes': notes
            }
        })
    except Exception as e:
        logger.error(f"获取播客详情失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/podcasts', methods=['POST'])
def create_podcast():
    """创建播客任务"""
    try:
        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({
                'success': False,
                'error': '缺少 URL 参数'
            }), 400

        # 创建播客记录
        podcast_id = db.create_podcast(url)

        # TODO: 提交到 Celery 任务队列
        # 目前先同步处理
        from main import process_podcast
        try:
            process_podcast(url, config, db)

            return jsonify({
                'success': True,
                'data': {
                    'podcast_id': podcast_id,
                    'message': '播客处理完成'
                }
            })
        except Exception as e:
            logger.error(f"处理播客失败: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    except Exception as e:
        logger.error(f"创建播客任务失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/notes/generate', methods=['POST'])
def generate_note():
    """生成笔记"""
    try:
        data = request.get_json()
        podcast_id = data.get('podcast_id')
        note_type = data.get('note_type', 'auto')  # auto 或 ai
        ai_provider = data.get('ai_provider', 'qwen')  # AI 提供商

        if not podcast_id:
            return jsonify({
                'success': False,
                'error': '缺少 podcast_id 参数'
            }), 400

        # 加载转录结果
        transcripts = db.get_transcripts_by_podcast(podcast_id)
        if not transcripts:
            return jsonify({
                'success': False,
                'error': '未找到转录记录'
            }), 404

        transcript_path = transcripts[0]['file_path']

        # 加载转录段落
        from utils.transcript_loader import load_transcript
        paragraphs = load_transcript(transcript_path)

        if note_type == 'auto':
            # 规则引擎笔记
            from analyzer import TextAnalyzer
            from note_generator import NoteGenerator

            analyzer = TextAnalyzer({
                'top_keywords': config.get('analyzer.top_keywords'),
                'top_sentences': config.get('analyzer.top_sentences'),
                'min_sentence_length': config.get('analyzer.min_sentence_length')
            })

            analysis_result = analyzer.analyze(paragraphs)

            generator = NoteGenerator()
            note = generator.generate_from_analysis(
                analysis_result,
                podcast_info={
                    'podcast_id': podcast_id,
                    'generated_at': '2026-02-24',
                    'duration': paragraphs[-1]['end'] if paragraphs else 0
                }
            )

            # 保存笔记
            output_path = Path(config.get('storage.note_dir')) / f"{podcast_id}_auto.md"
            generator.save_note(note, str(output_path))

            # 创建笔记记录
            db.create_note(podcast_id, 'auto', str(output_path))

            return jsonify({
                'success': True,
                'data': {
                    'note_type': 'auto',
                    'file_path': str(output_path),
                    'content': note
                }
            })

        elif note_type == 'ai':
            # AI 笔记
            from ai_note_generator import create_ai_generator

            # 检查 API Key
            api_key_field = f'ai.{ai_provider}_api_key'
            api_key = config.get(api_key_field)

            if not api_key:
                return jsonify({
                    'success': False,
                    'error': f'未配置 {ai_provider} API Key'
                }), 400

            generator = create_ai_generator(ai_provider, {
                f'{ai_provider}_api_key': api_key,
                f'{ai_provider}_model': config.get(f'ai.{ai_provider}_model'),
                'max_tokens': config.get('ai.max_tokens'),
                'temperature': config.get('ai.temperature'),
                'timeout': config.get('ai.timeout')
            })

            note = generator.generate(
                paragraphs,
                podcast_info={
                    'podcast_id': podcast_id,
                    'duration': paragraphs[-1]['end'] if paragraphs else 0
                }
            )

            # 保存笔记
            output_path = Path(config.get('storage.note_dir')) / f"{podcast_id}_{ai_provider}_ai.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(note)

            # 创建笔记记录
            db.create_note(podcast_id, 'ai', str(output_path), model_name=f'{ai_provider}-ai')

            return jsonify({
                'success': True,
                'data': {
                    'note_type': 'ai',
                    'ai_provider': ai_provider,
                    'file_path': str(output_path),
                    'content': note
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': f'不支持的笔记类型: {note_type}'
            }), 400

    except Exception as e:
        logger.error(f"生成笔记失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files/download', methods=['POST'])
def download_file_post():
    """下载文件（POST方式，避免URL编码问题）"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')

        if not file_path:
            return jsonify({
                'success': False,
                'error': '未提供文件路径'
            }), 400

        logger.info(f"下载请求 - 原始路径: {file_path}")

        # 处理路径（支持绝对路径和相对路径）
        file_path_obj = Path(file_path)
        if file_path_obj.is_absolute():
            full_path = file_path_obj
        else:
            full_path = project_root / file_path

        logger.info(f"下载请求 - 完整路径: {full_path}")

        if not full_path.exists():
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404

        # 获取文件名
        filename = full_path.name

        return send_file(
            full_path,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files/<path:file_path>', methods=['GET'])
def download_file(file_path):
    """下载文件（GET方式，保留兼容性）"""
    try:
        # 处理路径（支持绝对路径和相对路径）
        file_path_obj = Path(file_path)
        if file_path_obj.is_absolute():
            full_path = file_path_obj
        else:
            full_path = project_root / file_path

        if not full_path.exists():
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404

        # 获取文件名
        filename = full_path.name

        return send_file(
            full_path,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files/preview', methods=['POST'])
def preview_file():
    """预览文件（使用POST避免URL编码问题）"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')

        if not file_path:
            return jsonify({
                'success': False,
                'error': '未提供文件路径'
            }), 400

        logger.info(f"预览请求 - 原始路径: {file_path}")

        # 处理路径（支持绝对路径和相对路径）
        file_path_obj = Path(file_path)
        if file_path_obj.is_absolute():
            full_path = file_path_obj
        else:
            full_path = project_root / file_path

        logger.info(f"预览请求 - 完整路径: {full_path}")
        logger.info(f"预览请求 - 文件存在: {full_path.exists()}")

        if not full_path.exists():
            return jsonify({
                'success': False,
                'error': f'文件不存在: {full_path}'
            }), 404

        # 读取文件内容
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 根据文件类型处理
        if full_path.suffix == '.md':
            # Markdown 转 HTML
            html_content = markdown.markdown(
                content,
                extensions=['extra', 'codehilite', 'tables', 'toc']
            )
            return jsonify({
                'success': True,
                'data': {
                    'type': 'markdown',
                    'content': content,
                    'html': html_content
                }
            })
        else:
            # 纯文本
            return jsonify({
                'success': True,
                'data': {
                    'type': 'text',
                    'content': content
                }
            })
    except Exception as e:
        logger.error(f"预览文件失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files/preview/<path:file_path>', methods=['GET'])
def preview_file_get(file_path):
    """预览文件（GET方式，保留兼容性）"""
    try:
        logger.info(f"预览请求(GET) - 原始路径: {file_path}")

        # 处理路径（支持绝对路径和相对路径）
        file_path_obj = Path(file_path)
        if file_path_obj.is_absolute():
            full_path = file_path_obj
        else:
            full_path = project_root / file_path

        logger.info(f"预览请求(GET) - 完整路径: {full_path}")
        logger.info(f"预览请求(GET) - 文件存在: {full_path.exists()}")

        if not full_path.exists():
            return jsonify({
                'success': False,
                'error': f'文件不存在: {full_path}'
            }), 404

        # 读取文件内容
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 根据文件类型处理
        if full_path.suffix == '.md':
            # Markdown 转 HTML
            html_content = markdown.markdown(
                content,
                extensions=['extra', 'codehilite', 'tables', 'toc']
            )
            return jsonify({
                'success': True,
                'data': {
                    'type': 'markdown',
                    'content': content,
                    'html': html_content
                }
            })
        else:
            # 纯文本
            return jsonify({
                'success': True,
                'data': {
                    'type': 'text',
                    'content': content
                }
            })
    except Exception as e:
        logger.error(f"预览文件失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """获取设置"""
    try:
        settings = {
            'ai_providers': ['deepseek', 'claude', 'openai', 'doubao', 'qwen'],
            'default_provider': config.get('ai.default_provider'),
            'whisper_provider': config.get('whisper.api_provider')
        }
        return jsonify({
            'success': True,
            'data': settings
        })
    except Exception as e:
        logger.error(f"获取设置失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/podcasts/<podcast_id>', methods=['DELETE'])
def delete_podcast(podcast_id):
    """删除播客"""
    try:
        # 删除数据库记录
        success = db.delete_podcast(podcast_id)

        if not success:
            return jsonify({
                'success': False,
                'error': '删除数据库记录失败'
            }), 500

        # 删除文件
        file_result = delete_podcast_files(podcast_id, base_dirs)

        return jsonify({
            'success': True,
            'data': {
                'podcast_id': podcast_id,
                'files_deleted': len(file_result['deleted']),
                'files_failed': len(file_result['failed'])
            }
        })
    except Exception as e:
        logger.error(f"删除播客失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/podcasts/batch-delete', methods=['POST'])
def batch_delete_podcasts():
    """批量删除播客"""
    try:
        data = request.get_json()
        podcast_ids = data.get('podcast_ids', [])

        if not podcast_ids:
            return jsonify({
                'success': False,
                'error': '缺少 podcast_ids 参数'
            }), 400

        # 批量删除数据库记录
        deleted_count = db.delete_podcasts_batch(podcast_ids)

        # 批量删除文件
        total_files_deleted = 0
        total_files_failed = 0

        for podcast_id in podcast_ids:
            file_result = delete_podcast_files(podcast_id, base_dirs)
            total_files_deleted += len(file_result['deleted'])
            total_files_failed += len(file_result['failed'])

        return jsonify({
            'success': True,
            'data': {
                'podcasts_deleted': deleted_count,
                'files_deleted': total_files_deleted,
                'files_failed': total_files_failed
            }
        })
    except Exception as e:
        logger.error(f"批量删除播客失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/podcasts/clear-all', methods=['DELETE'])
def clear_all_podcasts():
    """清空所有播客"""
    try:
        # 获取所有播客 ID
        podcasts = db.get_all_podcasts()
        podcast_ids = [p['id'] for p in podcasts]

        # 清空数据库
        deleted_count = db.clear_all_podcasts()

        # 删除所有文件
        total_files_deleted = 0
        total_files_failed = 0

        for podcast_id in podcast_ids:
            file_result = delete_podcast_files(podcast_id, base_dirs)
            total_files_deleted += len(file_result['deleted'])
            total_files_failed += len(file_result['failed'])

        return jsonify({
            'success': True,
            'data': {
                'podcasts_deleted': deleted_count,
                'files_deleted': total_files_deleted,
                'files_failed': total_files_failed
            }
        })
    except Exception as e:
        logger.error(f"清空播客失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/podcasts/<podcast_id>/rename', methods=['PUT'])
def rename_podcast(podcast_id):
    """重命名播客"""
    try:
        data = request.get_json()
        new_title = data.get('title')

        if not new_title:
            return jsonify({
                'success': False,
                'error': '缺少 title 参数'
            }), 400

        # 清理文件名
        clean_title = sanitize_filename(new_title)

        # 更新数据库
        db.update_podcast(podcast_id, title=clean_title)

        # 重命名文件
        file_result = rename_podcast_files(podcast_id, clean_title, base_dirs)

        # 更新数据库中的文件路径
        if file_result['renamed']:
            for item in file_result['renamed']:
                old_path = item['old']
                new_path = item['new']

                # 更新转录记录
                if 'transcripts' in old_path:
                    transcripts = db.get_transcripts_by_podcast(podcast_id)
                    for transcript in transcripts:
                        if transcript['file_path'] in old_path:
                            cursor = db.conn.cursor()
                            cursor.execute(
                                "UPDATE transcripts SET file_path = ? WHERE id = ?",
                                (new_path, transcript['id'])
                            )
                            db.conn.commit()

                # 更新笔记记录
                if 'notes' in old_path:
                    notes = db.get_notes_by_podcast(podcast_id)
                    for note in notes:
                        if note['file_path'] in old_path:
                            cursor = db.conn.cursor()
                            cursor.execute(
                                "UPDATE notes SET file_path = ? WHERE id = ?",
                                (new_path, note['id'])
                            )
                            db.conn.commit()

        return jsonify({
            'success': True,
            'data': {
                'podcast_id': podcast_id,
                'new_title': clean_title,
                'files_renamed': len(file_result['renamed']),
                'files_failed': len(file_result['failed'])
            }
        })
    except Exception as e:
        logger.error(f"重命名播客失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """404 错误处理"""
    return jsonify({
        'success': False,
        'error': '资源不存在'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    return jsonify({
        'success': False,
        'error': '服务器内部错误'
    }), 500


if __name__ == '__main__':
    host = config.get('app.host', '127.0.0.1')
    port = config.get('app.port', 5000)
    debug = config.get('app.debug', False)

    logger.info(f"启动 Flask 应用: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
