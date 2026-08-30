from google_api_client import GoogleWorkspaceClient

if __name__ == "__main__":
    print("Google 연동 테스트를 시작합니다...")
    try:
        client = GoogleWorkspaceClient()
        print("✅ 구글 인증 성공! (token.json 파일이 생성되었습니다.)")
        
        print("최신 멘토링 메일을 스캔합니다...")
        text, subject = client.fetch_latest_meeting_notes()
        if text:
            print(f"✅ 메일 제목: {subject}")
            print(f"✅ 문서 내용 길이: {len(text)}자")
            print("성공적으로 내용을 긁어왔습니다!")
        else:
            print("최근 메일 중에 '회의록'이 포함된 구글 밋 메일이 없습니다.")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
