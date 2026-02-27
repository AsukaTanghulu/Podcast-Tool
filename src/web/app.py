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
import sqlite3

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config
from database import get_db
from loguru import logger
from utils.file_naming import sanitize_filename, rename_podcast_files, delete_podcast_files
from utils.file_migration import move_podcast_files_to_category
from storage_manager import StorageManager
from file_uploader import FileUploader
from ai_chat import create_ai_chat, AIChatError

# 创建 Flask 应用
app = Flask(__name__)
CORS(app)

# 加载配置（使用绝对路径）
config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
config = get_config(str(config_path))
app.config['SECRET_KEY'] = 'your-secret-key-here'  # 生产环境应使用环境变量

# 基础目录配置
project_root = Path(__file__).parent.parent.parent

# 初始化数据库
db_path = project_root / config.get("database.path")
db = get_db(str(db_path))

# 初始化存储管理器
storage = StorageManager(config)

# 初始化文件上传器
uploader = FileUploader(str(project_root / "data" / "uploads"))

# AI 对话会话存储（使用内存存储，生产环境应使用 Redis）
chat_sessions = {}

base_dirs = {
    'audio': project_root / config.get('storage.audio_dir'),
    'transcript': project_root / config.get('storage.transcript_dir'),
    'note': project_root / config.get('storage.note_dir')
}


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/db-editor')
def db_editor():
    """数据库编辑器页面"""
    return render_template('db_editor.html')


@app.route('/api/admin/sql', methods=['POST'])
def admin_execute_sql():
    """执行 SQL（支持查询与增删改）"""
    try:
        data = request.get_json() or {}
        sql = (data.get('sql') or '').strip()
        params = data.get('params', [])

        if not sql:
            return jsonify({
                'success': False,
                'error': 'SQL 不能为空'
            }), 400

        if ';' in sql.strip().rstrip(';'):
            return jsonify({
                'success': False,
                'error': '仅支持单条 SQL 语句'
            }), 400

        first_keyword = sql.split(None, 1)[0].upper() if sql else ''

        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if first_keyword in ('SELECT', 'WITH', 'PRAGMA'):
                cursor.execute(sql, params)
                rows = [dict(row) for row in cursor.fetchall()]
                return jsonify({
                    'success': True,
                    'data': {
                        'type': 'query',
                        'row_count': len(rows),
                        'rows': rows
                    }
                })

            cursor.execute(sql, params)
            conn.commit()
            return jsonify({
                'success': True,
                'data': {
                    'type': 'mutation',
                    'affected_rows': cursor.rowcount,
                    'last_row_id': cursor.lastrowid
                }
            })

    except sqlite3.Error as e:
        logger.error(f"SQL 执行失败: {e}")
        return jsonify({
            'success': False,
            'error': f'SQL 错误: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"数据库编辑器接口失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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

        # TODO: 提交到 Celery 任务队列
        # 目前先同步处理
        from main import process_podcast
        try:
            # process_podcast 会自己创建播客记录，不需要在这里创建
            podcast_id = process_podcast(url, config, db)

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


@app.route('/api/documentaries', methods=['POST'])
def upload_documentary():
    """上传纪录片文件"""
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '未找到上传文件'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '未选择文件'
            }), 400

        # 获取标题（可选）
        title = request.form.get('title', '')

        # 验证文件
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()  # 获取文件大小
        file.seek(0)  # 重置到文件开头

        is_valid, error_msg = uploader.validate_file(file.filename, file_size)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400

        # 创建纪录片记录
        if not title:
            title = Path(file.filename).stem  # 使用文件名（不含扩展名）作为标题

        documentary_id = db.create_podcast(
            url='',  # 纪录片没有 URL
            title=title
        )

        # 更新内容类型和原始文件名
        db.update_podcast(
            documentary_id,
            content_type='documentary',
            original_filename=file.filename
        )

        # 保存文件
        file_path = uploader.save_file(file, file.filename, documentary_id)

        # 获取文件信息
        file_type = uploader.get_file_type(file.filename)

        # 更新数据库
        db.update_podcast(
            documentary_id,
            status='pending',
            file_size=file_size
        )

        logger.info(f"纪录片文件上传成功: {documentary_id}, 文件: {file_path}")

        # 提交转录任务
        try:
            from main import process_documentary
            # 异步处理（这里暂时同步处理，后续可以改为 Celery）
            process_documentary(str(file_path), documentary_id, config, db)

            return jsonify({
                'success': True,
                'data': {
                    'documentary_id': documentary_id,
                    'title': title,
                    'file_type': file_type,
                    'file_size': file_size,
                    'message': '纪录片上传成功，正在处理中...'
                }
            })
        except Exception as e:
            logger.error(f"处理纪录片失败: {e}")
            db.update_podcast(documentary_id, status='failed', error_message=str(e))
            return jsonify({
                'success': False,
                'error': f'处理失败: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"上传纪录片失败: {e}")
        import traceback
        traceback.print_exc()
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

        # 优先使用 JSON 转录作为结构化数据源，避免 Markdown 解析造成信息损失
        transcript_path_obj = Path(transcript_path)
        transcript_candidates = [transcript_path_obj]

        if transcript_path_obj.suffix.lower() != '.json':
            transcript_candidates.append(transcript_path_obj.with_suffix('.json'))

            # 兼容目录结构: .../md/xxx.md -> .../json/xxx.json
            parts = list(transcript_path_obj.parts)
            if 'md' in parts:
                md_index = parts.index('md')
                json_path_obj = Path(*parts[:md_index], 'json', *parts[md_index + 1:]).with_suffix('.json')
                transcript_candidates.append(json_path_obj)

        resolved_transcript_path = transcript_path_obj
        for candidate in transcript_candidates:
            if candidate.exists() and candidate.suffix.lower() == '.json':
                resolved_transcript_path = candidate
                break

        # 加载转录段落
        from utils.transcript_loader import load_transcript
        paragraphs = load_transcript(str(resolved_transcript_path))

        # 校验转录内容，避免空文本导致不同播客产出同一模板笔记
        transcript_char_count = sum(len(str(p.get('text', '')).strip()) for p in paragraphs)
        logger.info(
            f"笔记生成输入检查: podcast_id={podcast_id}, transcript_path={transcript_path}, "
            f"resolved_path={resolved_transcript_path}, "
            f"paragraphs={len(paragraphs)}, chars={transcript_char_count}"
        )

        if not paragraphs or transcript_char_count < 50:
            return jsonify({
                'success': False,
                'error': '转录内容为空或解析失败，无法生成有效笔记。请先重新转录该播客。'
            }), 400

        # 获取播客信息（包含栏目）
        podcast = db.get_podcast(podcast_id)
        category = podcast.get('category', '') if podcast else ''

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

            # 保存笔记（使用分类存储）
            output_path = storage.get_note_path(podcast_id, 'auto', category, 'md')
            storage.ensure_directory(output_path)
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

            # 保存笔记（使用分类存储）
            output_path = storage.get_note_path(podcast_id, f'{ai_provider}_ai', category, 'md')
            storage.ensure_directory(output_path)
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


@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def delete_note_record(note_id):
    """删除笔记记录（仅删除数据库记录，不删除文件）"""
    try:
        deleted = db.delete_note(note_id)
        if not deleted:
            return jsonify({
                'success': False,
                'error': '笔记记录不存在或删除失败'
            }), 404

        return jsonify({
            'success': True,
            'data': {
                'note_id': note_id,
                'message': '笔记记录已删除（文件已保留）'
            }
        })
    except Exception as e:
        logger.error(f"删除笔记记录失败: {e}")
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
            'ai_providers': ['qwen', 'deepseek', 'openai', 'doubao'],  # 移除 claude（不兼容）
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
        # 先删除文件（在删除数据库记录之前，这样可以通过数据库找到文件）
        file_result = delete_podcast_files(podcast_id, base_dirs, db)

        # 再删除数据库记录
        success = db.delete_podcast(podcast_id)

        if not success:
            return jsonify({
                'success': False,
                'error': '删除数据库记录失败'
            }), 500

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

        # 先批量删除文件
        total_files_deleted = 0
        total_files_failed = 0

        for podcast_id in podcast_ids:
            file_result = delete_podcast_files(podcast_id, base_dirs, db)
            total_files_deleted += len(file_result['deleted'])
            total_files_failed += len(file_result['failed'])

        # 再批量删除数据库记录
        deleted_count = db.delete_podcasts_batch(podcast_ids)

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

        # 先删除所有文件
        total_files_deleted = 0
        total_files_failed = 0

        for podcast_id in podcast_ids:
            file_result = delete_podcast_files(podcast_id, base_dirs, db)
            total_files_deleted += len(file_result['deleted'])
            total_files_failed += len(file_result['failed'])

        # 再清空数据库
        deleted_count = db.clear_all_podcasts()

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

        # 清理文件名（用于文件系统）
        clean_title = sanitize_filename(new_title)

        # 更新数据库（使用原始标题，不是清理后的）
        db.update_podcast(podcast_id, title=new_title)

        # 重命名文件（使用清理后的标题作为文件名）
        file_result = rename_podcast_files(podcast_id, clean_title, base_dirs, db)

        # 更新数据库中的文件路径
        if file_result['renamed']:
            for item in file_result['renamed']:
                old_path = item['old']
                new_path = item['new']

                # 更新音频文件路径
                if 'audio' in old_path:
                    db.update_podcast(podcast_id, audio_file_path=new_path)

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


@app.route('/api/podcasts/<podcast_id>/category', methods=['PUT'])
def update_podcast_category(podcast_id):
    """更新播客栏目"""
    try:
        data = request.get_json()
        new_category = data.get('category', '')

        # 获取播客信息，获取旧栏目
        podcast = db.get_podcast(podcast_id)
        if not podcast:
            return jsonify({
                'success': False,
                'error': '播客不存在'
            }), 404

        old_category = podcast.get('category', '') or '未分类'
        new_category = new_category or '未分类'

        # 更新数据库
        db.update_podcast(podcast_id, category=new_category)

        # 迁移文件到新栏目
        if old_category != new_category:
            logger.info(f"迁移文件: {old_category} -> {new_category}")
            migration_result = move_podcast_files_to_category(
                podcast_id,
                old_category,
                new_category,
                base_dirs,
                db
            )

            return jsonify({
                'success': True,
                'data': {
                    'podcast_id': podcast_id,
                    'old_category': old_category,
                    'new_category': new_category,
                    'files_moved': len(migration_result['moved']),
                    'files_failed': len(migration_result['failed'])
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'podcast_id': podcast_id,
                    'category': new_category,
                    'message': '栏目未变化'
                }
            })

    except Exception as e:
        logger.error(f"更新播客栏目失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/podcasts/<podcast_id>/retry-transcription', methods=['POST'])
def retry_transcription(podcast_id):
    """重新转录播客/纪录片"""
    try:
        # 获取播客信息
        podcast = db.get_podcast(podcast_id)
        if not podcast:
            return jsonify({
                'success': False,
                'error': '播客不存在'
            }), 404

        # 检查内容类型
        content_type = podcast.get('content_type', 'podcast')

        # 获取音频文件路径
        audio_path = None
        audio_url = podcast.get('audio_url', '')

        if content_type == 'documentary':
            # 纪录片：从 uploads 目录查找文件
            original_filename = podcast.get('original_filename', '')
            if original_filename:
                # 根据 podcast_id 查找文件
                upload_dir = project_root / "data" / "uploads"
                # 获取文件扩展名
                file_ext = Path(original_filename).suffix
                audio_path = upload_dir / f"{podcast_id}{file_ext}"

                if not audio_path.exists():
                    return jsonify({
                        'success': False,
                        'error': f'上传的文件不存在: {audio_path}'
                    }), 404
        else:
            # 播客：从 audio 目录查找文件
            category = podcast.get('category', '')
            audio_dir = project_root / config.get('storage.audio_dir')

            # 尝试查找音频文件（支持多种格式）
            for ext in ['.m4a', '.mp3', '.wav', '.flac', '.aac']:
                if category:
                    # 先在栏目文件夹中查找
                    test_path = audio_dir / category / f"{podcast_id}{ext}"
                    if test_path.exists():
                        audio_path = test_path
                        break

                # 在根目录查找
                test_path = audio_dir / f"{podcast_id}{ext}"
                if test_path.exists():
                    audio_path = test_path
                    break

            if not audio_path:
                return jsonify({
                    'success': False,
                    'error': '未找到音频文件，请确保文件已下载'
                }), 404

        logger.info(f"开始重新转录: {podcast_id}, 文件: {audio_path}")

        # 更新状态为转录中
        db.update_podcast(podcast_id, status='transcribing', error_message='')

        # 调用转录函数
        try:
            if content_type == 'documentary':
                from main import process_documentary
                process_documentary(str(audio_path), podcast_id, config, db)
            else:
                from main import process_podcast_transcription
                # 创建一个简化的转录函数
                from transcriber_qwen import QwenTranscriber
                from storage_manager import StorageManager
                from transcript_formatter import format_transcript
                import json

                # 转录配置
                transcriber_config = {
                    "api_key": config.get("whisper.qwen_api_key"),
                    "language": config.get("whisper.language"),
                    "model": config.get("whisper.qwen_model", "paraformer-v2"),
                    "paragraph_gap": config.get("analyzer.paragraph_gap")
                }
                transcriber = QwenTranscriber(transcriber_config)

                # 执行转录
                paragraphs = transcriber.transcribe(str(audio_path), audio_url=audio_url)
                model_name = f"qwen-{transcriber_config['model']}"

                # 获取栏目信息
                category = podcast.get('category', '')
                title = podcast.get('title', '未命名播客')

                # 初始化存储管理器
                storage = StorageManager(config)

                # 保存 JSON 文件（作为标准转录数据源）
                transcript_json_path = storage.get_transcript_path(podcast_id, category, "json")
                storage.ensure_directory(transcript_json_path)

                json_data = {
                    "segments": paragraphs,
                    "metadata": {
                        "podcast_id": podcast_id,
                        "title": title,
                        "model": model_name,
                        "category": category or "未分类",
                        "speaker_names": {}
                    },
                    "word_count": sum(len(p["text"]) for p in paragraphs),
                    "paragraph_count": len(paragraphs)
                }

                with open(transcript_json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)

                # 生成 Markdown 文件
                transcript_md_path = storage.get_transcript_path(podcast_id, category, "md")
                storage.ensure_directory(transcript_md_path)

                format_transcript(
                    paragraphs,
                    metadata={
                        "podcast_id": podcast_id,
                        "title": title,
                        "model": model_name,
                        "category": category or "未分类"
                    },
                    output_format='markdown',
                    output_path=str(transcript_md_path)
                )

                # 生成 PDF 文件（可选）
                try:
                    transcript_pdf_path = storage.get_transcript_path(podcast_id, category, "pdf")
                    storage.ensure_directory(transcript_pdf_path)

                    format_transcript(
                        paragraphs,
                        metadata={
                            "podcast_id": podcast_id,
                            "title": title,
                            "model": model_name,
                            "category": category or "未分类"
                        },
                        output_format='pdf',
                        output_path=str(transcript_pdf_path)
                    )
                except Exception as e:
                    logger.warning(f"PDF 生成失败: {e}")

                # 创建或更新转录记录
                word_count = sum(len(p["text"]) for p in paragraphs)

                # 检查是否已有转录记录
                existing_transcripts = db.get_transcripts_by_podcast(podcast_id)
                if existing_transcripts:
                    # 更新现有记录
                    cursor = db.conn.cursor()
                    cursor.execute("""
                        UPDATE transcripts
                        SET file_path = ?, word_count = ?, model_version = ?
                        WHERE id = ?
                    """, (str(transcript_json_path), word_count, model_name, existing_transcripts[0]['id']))
                    db.conn.commit()
                else:
                    # 创建新记录
                    db.create_transcript(
                        podcast_id,
                        str(transcript_json_path),
                        word_count=word_count,
                        model_version=model_name
                    )

                # 更新播客状态
                db.update_podcast(podcast_id, status='completed')

                logger.info(f"重新转录成功: {podcast_id}")

            return jsonify({
                'success': True,
                'data': {
                    'podcast_id': podcast_id,
                    'message': '重新转录成功'
                }
            })

        except Exception as e:
            logger.error(f"重新转录失败: {e}")
            import traceback
            traceback.print_exc()
            db.update_podcast(podcast_id, status='failed', error_message=str(e))
            return jsonify({
                'success': False,
                'error': f'转录失败: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"重新转录请求失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/transcripts/<transcript_id>/speakers', methods=['GET'])
def get_speakers(transcript_id):
    """获取转录中的说话人列表"""
    try:
        # 获取转录记录
        cursor = db.conn.cursor()
        cursor.execute("SELECT file_path FROM transcripts WHERE id = ?", (transcript_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({
                'success': False,
                'error': '转录记录不存在'
            }), 404

        file_path = result[0]

        # 读取转录文件
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 提取说话人列表
        speakers = {}
        for segment in data.get('segments', []):
            speaker_id = segment.get('speaker_id')
            if speaker_id is not None and str(speaker_id).strip() != '':
                speaker_key = str(speaker_id)
                if speaker_key not in speakers:
                    speakers[speaker_key] = {
                        'id': speaker_key,
                        'name': speaker_key,  # 默认使用 ID 作为名称
                        'count': 0
                    }
                speakers[speaker_key]['count'] += 1

        return jsonify({
            'success': True,
            'data': {
                'transcript_id': transcript_id,
                'speakers': list(speakers.values())
            }
        })
    except Exception as e:
        logger.error(f"获取说话人列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/transcripts/<transcript_id>/speakers/rename', methods=['PUT'])
def rename_speaker(transcript_id):
    """重命名说话人"""
    try:
        data = request.get_json()
        speaker_mappings = data.get('mappings', {})  # {speaker_id: new_name}

        if not speaker_mappings:
            return jsonify({
                'success': False,
                'error': '缺少 mappings 参数'
            }), 400

        # 获取转录记录
        cursor = db.conn.cursor()
        cursor.execute("SELECT file_path FROM transcripts WHERE id = ?", (transcript_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({
                'success': False,
                'error': '转录记录不存在'
            }), 404

        file_path = result[0]

        # 读取转录文件
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 添加说话人映射到元数据
        if 'metadata' not in data:
            data['metadata'] = {}
        data['metadata']['speaker_names'] = speaker_mappings

        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return jsonify({
            'success': True,
            'data': {
                'transcript_id': transcript_id,
                'mappings': speaker_mappings
            }
        })
    except Exception as e:
        logger.error(f"重命名说话人失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/transcripts/<transcript_id>/export', methods=['POST'])
def export_transcript(transcript_id):
    """导出转录文本（支持说话人标记）"""
    try:
        data = request.get_json()
        format_type = data.get('format', 'txt')  # txt, md, srt
        include_speakers = data.get('include_speakers', True)
        include_timestamps = data.get('include_timestamps', True)

        # 获取转录记录
        cursor = db.conn.cursor()
        cursor.execute("SELECT file_path, podcast_id FROM transcripts WHERE id = ?", (transcript_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({
                'success': False,
                'error': '转录记录不存在'
            }), 404

        file_path, podcast_id = result

        # 读取转录文件
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        segments = data.get('segments', [])
        speaker_names = data.get('metadata', {}).get('speaker_names', {})

        # 生成导出内容
        if format_type == 'txt':
            lines = []
            for seg in segments:
                if include_timestamps:
                    start = _format_time(seg['start'])
                    end = _format_time(seg['end'])
                    lines.append(f"[{start} - {end}]")

                if include_speakers and seg.get('speaker_id'):
                    speaker_id = seg['speaker_id']
                    speaker_name = speaker_names.get(speaker_id, speaker_id)
                    lines.append(f"说话人: {speaker_name}")

                lines.append(seg['text'])
                lines.append("")

            content = "\n".join(lines)
            filename = f"{podcast_id}_transcript.txt"

        elif format_type == 'md':
            lines = ["# 转录文本\n"]
            for seg in segments:
                if include_timestamps:
                    start = _format_time(seg['start'])
                    end = _format_time(seg['end'])
                    lines.append(f"**[{start} - {end}]**")

                if include_speakers and seg.get('speaker_id'):
                    speaker_id = seg['speaker_id']
                    speaker_name = speaker_names.get(speaker_id, speaker_id)
                    lines.append(f"*{speaker_name}:*")

                lines.append(f"\n{seg['text']}\n")

            content = "\n".join(lines)
            filename = f"{podcast_id}_transcript.md"

        elif format_type == 'srt':
            lines = []
            for i, seg in enumerate(segments, 1):
                lines.append(str(i))
                start = _format_srt_time(seg['start'])
                end = _format_srt_time(seg['end'])
                lines.append(f"{start} --> {end}")

                text = seg['text']
                if include_speakers and seg.get('speaker_id'):
                    speaker_id = seg['speaker_id']
                    speaker_name = speaker_names.get(speaker_id, speaker_id)
                    text = f"[{speaker_name}] {text}"

                lines.append(text)
                lines.append("")

            content = "\n".join(lines)
            filename = f"{podcast_id}_transcript.srt"
        else:
            return jsonify({
                'success': False,
                'error': f'不支持的格式: {format_type}'
            }), 400

        # 创建临时文件
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                                 suffix=f'.{format_type}', delete=False)
        temp_file.write(content)
        temp_file.close()

        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"导出转录失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _format_time(seconds):
    """格式化时间为 HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _format_srt_time(seconds):
    """格式化时间为 SRT 格式 HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


@app.route('/api/podcasts/<podcast_id>/chat/init', methods=['POST'])
def init_chat(podcast_id):
    """初始化 AI 对话会话"""
    try:
        data = request.get_json()
        provider = data.get('provider', 'deepseek')  # 默认使用 deepseek

        # 获取播客信息
        podcast = db.get_podcast(podcast_id)
        if not podcast:
            return jsonify({
                'success': False,
                'error': '播客不存在'
            }), 404

        # 获取转录记录
        transcripts = db.get_transcripts_by_podcast(podcast_id)
        if not transcripts:
            return jsonify({
                'success': False,
                'error': '未找到转录记录，请先完成转录'
            }), 404

        transcript_path = transcripts[0]['file_path']

        # 读取转录文本
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
        except Exception as e:
            logger.error(f"读取转录文件失败: {e}")
            return jsonify({
                'success': False,
                'error': f'读取转录文件失败: {str(e)}'
            }), 500

        # 创建 AI 对话实例
        try:
            chat_config = {
                'qwen_api_key': config.get('ai.qwen_api_key'),
                'qwen_model': config.get('ai.qwen_model', 'qwen-plus'),
                'deepseek_api_key': config.get('ai.deepseek_api_key'),
                'deepseek_model': config.get('ai.deepseek_model', 'deepseek-chat'),
                'max_tokens': config.get('ai.max_tokens', 2000),
                'temperature': config.get('ai.temperature', 0.7)
            }

            chat = create_ai_chat(provider, chat_config)

            # 设置转录上下文
            metadata = {
                'title': podcast.get('title', '未命名播客'),
                'category': podcast.get('category', ''),
                'duration': podcast.get('duration', 0)
            }
            chat.set_transcript_context(transcript_text, metadata)

            # 生成会话 ID
            session_id = f"{podcast_id}_{provider}"

            # 保存会话
            chat_sessions[session_id] = chat

            logger.info(f"初始化 AI 对话会话: {session_id}")

            return jsonify({
                'success': True,
                'data': {
                    'session_id': session_id,
                    'provider': provider,
                    'message': 'AI 对话会话已初始化，你可以开始提问了'
                }
            })

        except AIChatError as e:
            logger.error(f"创建 AI 对话失败: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400

    except Exception as e:
        logger.error(f"初始化 AI 对话失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chat/<session_id>/message', methods=['POST'])
def send_chat_message(session_id):
    """发送对话消息"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({
                'success': False,
                'error': '消息不能为空'
            }), 400

        # 获取会话
        chat = chat_sessions.get(session_id)
        if not chat:
            return jsonify({
                'success': False,
                'error': '会话不存在或已过期，请重新初始化'
            }), 404

        # 发送消息并获取回复
        try:
            assistant_reply = chat.chat(user_message)

            return jsonify({
                'success': True,
                'data': {
                    'message': assistant_reply,
                    'session_id': session_id
                }
            })

        except AIChatError as e:
            logger.error(f"AI 对话失败: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    except Exception as e:
        logger.error(f"发送对话消息失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chat/<session_id>/history', methods=['GET'])
def get_chat_history(session_id):
    """获取对话历史"""
    try:
        # 获取会话
        chat = chat_sessions.get(session_id)
        if not chat:
            return jsonify({
                'success': False,
                'error': '会话不存在或已过期'
            }), 404

        history = chat.get_conversation_history()

        return jsonify({
            'success': True,
            'data': {
                'history': history,
                'session_id': session_id
            }
        })

    except Exception as e:
        logger.error(f"获取对话历史失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chat/<session_id>/clear', methods=['POST'])
def clear_chat_history(session_id):
    """清空对话历史"""
    try:
        # 获取会话
        chat = chat_sessions.get(session_id)
        if not chat:
            return jsonify({
                'success': False,
                'error': '会话不存在或已过期'
            }), 404

        chat.clear_history()

        return jsonify({
            'success': True,
            'data': {
                'message': '对话历史已清空',
                'session_id': session_id
            }
        })

    except Exception as e:
        logger.error(f"清空对话历史失败: {e}")
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
