"""Local work-context editor. These routes never call an LLM or Notion."""
from flask import Blueprint, jsonify, request
from pydantic import ValidationError
from mentoring.services.mentor_context import (
    load_context, save_context, delete_context, approved_context, ContextConflict,
)

context_routes = Blueprint('mentor_context', __name__)


@context_routes.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


@context_routes.route('/api/mentor-context', methods=['GET', 'PUT', 'DELETE'])
def mentor_context_endpoint():
    if request.method != 'GET':
        origin = request.headers.get('Origin')
        if origin and origin.rstrip('/') != request.host_url.rstrip('/'):
            return jsonify(success=False, error='다른 사이트에서 설정을 변경할 수 없습니다.'), 403
        if not request.is_json:
            return jsonify(success=False, error='JSON 요청이 필요합니다.'), 415
        if request.content_length and request.content_length > 250000:
            return jsonify(success=False, error='입력이 너무 큽니다. 필요한 업무 내용만 요약하세요.'), 413
    try:
        if request.method == 'PUT':
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return jsonify(success=False, error='유효한 설정 객체가 필요합니다.'), 400
            context = save_context(data)
        elif request.method == 'DELETE':
            data = request.get_json(silent=True)
            if not isinstance(data, dict) or not isinstance(data.get('revision'), str):
                return jsonify(success=False, error='삭제할 설정의 버전이 필요합니다.'), 400
            delete_context(data['revision'])
            context = load_context()
        else:
            context = load_context()
        return jsonify(success=True, data=context.model_dump(), preview=approved_context(context))
    except ContextConflict:
        return jsonify(success=False, error='다른 화면에서 설정이 변경되었습니다. 새로 불러온 뒤 저장하세요.'), 409
    except (ValidationError, ValueError):
        return jsonify(success=False, error='설정 형식·길이를 확인하세요. 전체 50,000자, 서비스 8개, 메모 12개까지 저장할 수 있습니다.'), 400
    except OSError:
        return jsonify(success=False, error='로컬 업무 맥락 파일을 읽거나 저장할 수 없습니다.'), 500
