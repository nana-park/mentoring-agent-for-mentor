/* Work-context UI: local file reading, explicit review, no automatic ChatGPT access. */
(() => {
    'use strict';
    const byId = id => document.getElementById(id);
    let revision = '', loaded = false, dirty = false, savedResponse = null;
    const status = (message, error = false) => {
        byId('context-status').textContent = message;
        byId('context-status').classList.toggle('error', error);
    };
    const changed = () => { dirty = true; status('저장하지 않은 변경 사항이 있습니다. 미리보기는 마지막 저장본입니다.'); };
    function inputField(label, value, key, max, multiline = false) {
        const wrapper = document.createElement('label');
        wrapper.className = 'context-field';
        wrapper.append(document.createTextNode(label));
        const control = document.createElement(multiline ? 'textarea' : 'input');
        if (multiline) control.rows = key === 'text' ? 6 : 4;
        control.value = value || '';
        control.maxLength = max;
        control.dataset.field = key;
        wrapper.append(control);
        return wrapper;
    }
    function addCard(kind, item = {}, markDirty = true) {
        const list = byId(kind === 'service' ? 'context-services' : 'context-notes');
        if (list.children.length >= (kind === 'service' ? 8 : 12)) {
            status('더 추가할 수 없습니다. 기존 항목을 정리해주세요.', true); return;
        }
        const card = document.createElement('div');
        card.className = 'context-card';
        card.dataset.id = item.id || '';
        if (kind === 'service') {
            card.append(inputField('서비스 이름', item.name, 'name', 120));
            card.append(inputField('사용자 · AI 기능 · 진행 단계 · 해결할 문제 · 제약', item.details, 'details', 3000, true));
        } else {
            card.append(inputField('메모 제목', item.title, 'title', 160));
            card.append(inputField('출처 / 기준 시점', item.source || '직접 입력', 'source', 160));
            card.append(inputField('검토할 업무 맥락 (메모당 12,000자)', item.text, 'text', 12000, true));
        }
        const footer = document.createElement('div'); footer.className = 'context-card-footer';
        const label = document.createElement('label'); label.className = 'context-check';
        const approved = document.createElement('input'); approved.type = 'checkbox';
        approved.checked = Boolean(item.approved); approved.dataset.field = 'approved';
        label.append(approved, document.createTextNode('현재 내용 확인 완료 · 분석 사용'));
        const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '항목 제거';
        remove.addEventListener('click', () => { card.remove(); changed(); });
        footer.append(label, remove); card.append(footer); list.append(card);
        if (markDirty) changed();
    }
    function collectCards(id) {
        return [...byId(id).children].map(card => {
            const item = {};
            if (card.dataset.id) item.id = card.dataset.id;
            card.querySelectorAll('[data-field]').forEach(input => {
                item[input.dataset.field] = input.type === 'checkbox' ? input.checked : input.value.trim();
            });
            return item;
        });
    }
    function render(response) {
        savedResponse = response;
        const data = response.data;
        revision = data.revision;
        byId('context-role').value = data.role;
        byId('context-goals').value = data.goals;
        byId('context-enabled').checked = data.enabled;
        byId('context-services').replaceChildren(); byId('context-notes').replaceChildren();
        data.services.forEach(item => addCard('service', item, false));
        data.notes.forEach(item => addCard('note', item, false));
        const preview = response.preview;
        byId('context-preview').textContent = Object.keys(preview).length ? [
            `내 역할: ${preview.role || '미입력'}`,
            `업무 목표: ${preview.goals || '미입력'}`,
            '', '검토한 서비스',
            ...(preview.services.length ? preview.services.map(item => `• ${item.name}\n${item.details}`) : ['선택한 서비스 없음']),
            '', '검토한 업무 메모',
            ...(preview.notes.length ? preview.notes.map(item => `• ${item.title}\n${item.source}\n${item.text}`) : ['선택한 메모 없음'])
        ].join('\n') : '사용 꺼짐 — 업무 맥락을 전달하지 않음';
        loaded = true; dirty = false;
    }
    async function request(method = 'GET', data) {
        const options = {method};
        if (data !== undefined) {
            options.headers = {'Content-Type': 'application/json'};
            options.body = JSON.stringify(data);
        }
        const res = await fetch('/api/mentor-context', options);
        const body = await res.json();
        if (!res.ok || !body.success) throw new Error(body.error || '요청을 처리하지 못했습니다.');
        return body;
    }
    async function load(force = false) {
        if (loaded && !force) return;
        if (dirty && !window.confirm('저장하지 않은 변경을 버리고 저장본을 불러올까요?')) return;
        try { render(await request()); status('저장본을 불러왔습니다. 저장하거나 읽는 동작은 AI를 호출하지 않습니다.'); }
        catch (e) { status(e.message, true); }
    }
    byId('context-save').addEventListener('click', async () => {
        const button = byId('context-save'); button.disabled = true;
        try {
            const data = {revision, enabled: byId('context-enabled').checked,
                role: byId('context-role').value.trim(), goals: byId('context-goals').value.trim(),
                services: collectCards('context-services'), notes: collectCards('context-notes')};
            render(await request('PUT', data));
            status('로컬에 저장했습니다. 다음 분석부터 저장한 사용 설정이 적용됩니다.');
        } catch (e) { status(e.message, true); }
        finally { button.disabled = false; }
    });
    byId('context-delete').addEventListener('click', async () => {
        if (!window.confirm('이 PC에 저장한 업무 맥락 전체를 삭제할까요? 이미 Notion에 저장한 인사이트는 남습니다.')) return;
        try { render(await request('DELETE', {revision})); status('로컬 업무 맥락을 삭제했습니다.'); }
        catch (e) { status(e.message, true); }
    });
    byId('context-reload').addEventListener('click', () => load(true));
    byId('context-add-service').addEventListener('click', () => addCard('service'));
    byId('context-add-note').addEventListener('click', () => addCard('note'));
    byId('context-copy-prompt').addEventListener('click', async () => {
        try { await navigator.clipboard.writeText(byId('context-chatgpt-prompt').value); status('ChatGPT에 붙여넣을 요청문을 복사했습니다.'); }
        catch (_) { byId('context-chatgpt-prompt').select(); status('요청문을 선택했습니다. Ctrl+C로 복사해주세요.'); }
    });
    byId('context-import').addEventListener('change', async event => {
        const file = event.target.files[0];
        if (!file) return;
        try {
            if (!/\.(txt|md)$/i.test(file.name) || file.size > 64000) throw new Error('64KB 이하의 .txt 또는 .md 메모만 가져올 수 있습니다.');
            const text = await file.text();
            if (!text.trim() || text.length > 12000) throw new Error('메모는 비어 있지 않은 12,000자 이하 텍스트여야 합니다. 먼저 요약해주세요.');
            addCard('note', {title: file.name.slice(0, 160), source: '가져온 텍스트 · 출처/시점 확인 필요', text, approved: false});
        } catch (e) { status(e.message, true); }
        finally { event.target.value = ''; }
    });
    byId('context-view').addEventListener('input', event => {
        if (event.target.id !== 'context-chatgpt-prompt' && event.target.type !== 'file') {
            const card = event.target.closest('.context-card');
            if (card && event.target.type !== 'checkbox') {
                card.querySelector('[data-field="approved"]').checked = false;
            }
            changed();
        }
    });
    window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
    const drawer = byId('context-view');
    let opener = null, closing = false, previousOverflow = '';
    function open() {
        if (drawer.open || closing) return;
        opener = document.activeElement;
        previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        drawer.showModal();
        requestAnimationFrame(() => drawer.classList.add('is-open'));
        load();
    }
    function close() {
        if (closing || !drawer.open) return;
        if (byId('context-save').disabled) { status('저장 중입니다. 잠시 기다려주세요.'); return; }
        if (dirty) {
            if (!window.confirm('저장하지 않은 변경을 버리고 닫을까요?')) return;
            if (savedResponse) render(savedResponse);
            dirty = false;
        }
        closing = true;
        drawer.classList.remove('is-open');
        const delay = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 200;
        window.setTimeout(() => { drawer.close(); closing = false; }, delay);
    }
    drawer.addEventListener('cancel', event => { event.preventDefault(); close(); });
    drawer.addEventListener('click', event => {
        const rect = drawer.getBoundingClientRect();
        if (event.target === drawer && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) close();
    });
    drawer.addEventListener('close', () => {
        document.body.style.overflow = previousOverflow;
        if (opener && opener.isConnected) opener.focus({preventScroll: true});
    });
    byId('context-close').addEventListener('click', close);
    byId('context-close-top').addEventListener('click', close);
    window.mentorContextUI = {load, open, close};
})();
