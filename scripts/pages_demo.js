/* GitHub Pages demo: all application requests stay in this tab's memory. */
(() => {
    'use strict';
    let version = 0;
    const empty = () => ({revision: String(++version), enabled: false, role: '', goals: '', services: [], notes: []});
    let context = empty();
    const json = (body, status = 200) => new Response(JSON.stringify(body), {
        status, headers: {'Content-Type': 'application/json'}
    });
    const contextResponse = () => json({success: true, data: context, preview: context.enabled ? {
        demo: '미리보기 전용 — 외부로 전송하지 않습니다', role: context.role, goals: context.goals,
        services: context.services.filter(item => item.approved), notes: context.notes.filter(item => item.approved)
    } : {}});
    const sample = '[데모] 학생 A: AI 답변의 출처가 보이지 않으면 신뢰하기 어렵다고 말했다.\n이 내용은 입력을 분석한 결과가 아닌 준비된 가상 예시입니다.';
    // Fail closed: never delegate to native fetch, including unknown routes.
    window.fetch = async (input, options = {}) => {
        const path = new URL(typeof input === 'string' ? input : input.url, location.href).pathname;
        const method = (options.method || 'GET').toUpperCase();
        if (path === '/api/mentor-context') {
            if (method === 'PUT' || method === 'DELETE') {
                const data = JSON.parse(options.body || '{}');
                if (data.revision !== context.revision) return json({success: false, error: '저장본을 다시 불러오세요.'}, 409);
                context = method === 'DELETE' ? empty() : {
                    revision: String(++version), enabled: Boolean(data.enabled),
                    role: String(data.role || ''), goals: String(data.goals || ''),
                    services: (data.services || []).slice(0, 8).map((item, i) => ({...item, id: `demo-service-${i}`})),
                    notes: (data.notes || []).slice(0, 12).map((item, i) => ({...item, id: `demo-note-${i}`}))
                };
            } else if (method !== 'GET') return json({success: false}, 405);
            return contextResponse();
        }
        if (path.startsWith('/api/docs/') && method === 'GET') {
            const name = path.split('/').pop();
            return Object.hasOwn(window.MENTORING_DEMO_DOCS, name)
                ? json({success: true, content: window.MENTORING_DEMO_DOCS[name]})
                : json({success: false, error: '데모에 포함되지 않은 문서입니다.'}, 404);
        }
        if (path === '/api/history') return json({success: true, data: [
            {title: '[데모] 멘토 업무 인사이트 예시', type: 'Demo', status: 'Success', date: '2026-01-01T09:00:00'}
        ]});
        if (path === '/api/automation') return json({success: true, config: {enabled: false, frequency: 'daily', day: 'Monday', time: '09:00'}});
        if (path === '/api/run/direct/analyze') return json({success: true, students: [{name: '[데모] 학생 A', content: sample}]});
        if (/^\/api\/stop\/(auto|batch|summarize|direct)$/.test(path)) return json({success: true});
        if (/^\/api\/run\/(auto|batch|summarize|direct)$/.test(path)) {
            const logs = [
                '[데모] 준비된 예시를 표시합니다. 입력 분석·메일 조회·Notion 기록은 하지 않습니다.',
                sample,
                '대화 기반 발견: 답변의 근거를 확인할 수 있는 경험이 중요할 수 있습니다.',
                '업무 적용 가설 [검증 전]: AI 지식검색 서비스에 출처 미리보기를 적용해보세요. 아래는 고정 예시이며 등록한 업무 맥락의 분석 결과가 아닙니다.',
                '작은 실험: 출처 표시 유무에 따른 답변 검증 과정을 5명에게 관찰합니다.',
                '판단 기준: 근거 확인 시간과 오답 발견 여부를 비교합니다.',
                '조건·한계: 가상 대화 하나로 실제 사용자 수요를 일반화할 수 없습니다.',
                '[데모] 처리 완료 — 실제 데이터는 생성하거나 전송하지 않았습니다.'
            ];
            return new Response([...logs.map(log => ({log})), {success: true}]
                .map(data => `data: ${JSON.stringify(data)}\n\n`).join(''),
                {headers: {'Content-Type': 'text/event-stream'}});
        }
        return json({success: false, error: '화면 데모에서는 지원하지 않는 요청입니다.'}, 404);
    };
})();
