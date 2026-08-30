import os
import subprocess
import sys

def main():
    print("📁 [수동 일괄 처리 모드] 로컬 메모(txt) 스캔 및 노션 업로드를 시작합니다...")
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(current_dir)
        subprocess.check_call([sys.executable, "main.py", "--mode", "batch"])
        print("\n✅ 모든 처리가 완료되었습니다!")
    except Exception as e:
        print(f"\n❌ 에러가 발생했습니다: {e}")
    finally:
        input("\n엔터를 누르면 종료됩니다...")

if __name__ == "__main__":
    main()
