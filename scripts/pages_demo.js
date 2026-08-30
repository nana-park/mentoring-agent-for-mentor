/* GitHub Pages demo: all application requests stay in this tab's memory. */
(() => {
    'use strict';
    let version = 0;
    const empty = () => ({revision: String(++version), enabled: false, role: '', goals: '', services: [], notes: []});
    let context = empty();
    let automation = {enabled: false, frequency: 'daily', day: 'Monday', time: '09:00'};
    const json = (body, status = 200) => new Response(JSON.stringify(body), {
        status, headers: {'Content-Type': 'application/json'}
    });
    const contextResponse = () => json({success: true, data: context, preview: context.enabled ? {
        notice: '미리보기 전용 — 외부로 전송하지 않습니다', role: context.role, goals: context.goals,
        services: context.services.filter(item => item.approved), notes: context.notes.filter(item => item.approved)
    } : {}});
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
                : json({success: false, error: '제공되지 않은 문서입니다.'}, 404);
        }
        if (path === '/api/history') return json({success: true, data: []});
        if (path === '/api/automation') {
            if (method === 'POST') {
                const data = JSON.parse(options.body || '{}');
                automation = {enabled: Boolean(data.enabled), frequency: data.frequency,
                    day: data.day, time: data.time};
            } else if (method !== 'GET') return json({success: false}, 405);
            // UI preference only; no timers, jobs, or external calls are created.
            return json({success: true, config: automation});
        }
        if (path.startsWith('/api/run/') || path.startsWith('/api/stop/')) return json({success: false, error: '웹 버전은 준비 중입니다. 실제 작업은 로컬 앱에서 실행해주세요.'}, 503);
        return json({success: false, error: '외부 서비스 연결 전에는 사용할 수 없는 기능입니다.'}, 404);
    };
})();
