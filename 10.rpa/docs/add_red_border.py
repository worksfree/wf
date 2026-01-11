"""
이미지에 적색 경계선 추가 스크립트

사용법:
1. 스크린샷을 images/ 폴더에 저장
2. 이 스크립트로 버튼/영역에 적색 경계선 추가
3. 처리된 이미지는 자동으로 덮어쓰기됨

필요 패키지:
pip install pillow

예제:
python add_red_border.py images/be_01_app_launch.png 100 50 200 100
                          (이미지 경로)            (x)  (y) (w)  (h)
"""

from PIL import Image, ImageDraw
import sys
from pathlib import Path


def add_red_border(image_path: str, x: int, y: int, width: int, height: int, border_width: int = 5):
    """
    이미지에 적색 경계선 추가
    
    Args:
        image_path: 이미지 파일 경로
        x: 경계선 시작 x 좌표
        y: 경계선 시작 y 좌표
        width: 경계선 너비
        height: 경계선 높이
        border_width: 경계선 두께 (기본값: 5px)
    """
    try:
        # 이미지 열기
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        # 적색 경계선 그리기 (두꺼운 선)
        for i in range(border_width):
            draw.rectangle(
                [x + i, y + i, x + width - i, y + height - i],
                outline='red',
                width=1
            )
        
        # 저장 (덮어쓰기)
        img.save(image_path)
        print(f"✅ 적색 경계선 추가 완료: {image_path}")
        print(f"   위치: ({x}, {y}), 크기: {width}x{height}, 두께: {border_width}px")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)


def add_red_border_interactive(image_path: str):
    """
    대화형 모드: 사용자가 좌표를 입력하여 경계선 추가
    """
    try:
        img = Image.open(image_path)
        print(f"\n이미지 크기: {img.width} x {img.height}")
        print("\n경계선을 추가할 영역의 좌표를 입력하세요:")
        
        x = int(input("  X 좌표 (좌상단): "))
        y = int(input("  Y 좌표 (좌상단): "))
        width = int(input("  너비: "))
        height = int(input("  높이: "))
        border_width = int(input("  경계선 두께 (기본 5px): ") or "5")
        
        add_red_border(image_path, x, y, width, height, border_width)
        
    except ValueError:
        print("❌ 올바른 숫자를 입력하세요.")
        sys.exit(1)


def batch_process(config_file: str):
    """
    배치 처리: JSON 설정 파일을 읽어서 여러 이미지 처리
    
    config_file 형식 (JSON):
    {
        "images": [
            {
                "path": "images/be_01_app_launch.png",
                "borders": [
                    {"x": 100, "y": 50, "width": 200, "height": 100, "thickness": 5}
                ]
            }
        ]
    }
    """
    import json
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        for img_config in config.get('images', []):
            img_path = img_config['path']
            print(f"\n처리 중: {img_path}")
            
            # 이미지 열기
            img = Image.open(img_path)
            draw = ImageDraw.Draw(img)
            
            # 여러 경계선 추가
            for border in img_config.get('borders', []):
                x = border['x']
                y = border['y']
                width = border['width']
                height = border['height']
                thickness = border.get('thickness', 5)
                
                # 경계선 그리기
                for i in range(thickness):
                    draw.rectangle(
                        [x + i, y + i, x + width - i, y + height - i],
                        outline='red',
                        width=1
                    )
                
                print(f"  ✅ 경계선 추가: ({x}, {y}) {width}x{height}")
            
            # 저장
            img.save(img_path)
            print(f"  💾 저장 완료: {img_path}")
        
        print(f"\n🎉 배치 처리 완료: {len(config['images'])}개 이미지")
        
    except FileNotFoundError:
        print(f"❌ 설정 파일을 찾을 수 없습니다: {config_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법:")
        print("  1. 단일 이미지 (명령행 인자):")
        print("     python add_red_border.py <이미지경로> <x> <y> <width> <height> [두께]")
        print()
        print("  2. 단일 이미지 (대화형):")
        print("     python add_red_border.py <이미지경로>")
        print()
        print("  3. 배치 처리 (JSON 설정 파일):")
        print("     python add_red_border.py --batch <설정파일.json>")
        print()
        print("예제:")
        print("  python add_red_border.py images/be_01.png 100 50 200 100 5")
        print("  python add_red_border.py images/be_01.png")
        print("  python add_red_border.py --batch border_config.json")
        sys.exit(1)
    
    # 배치 처리 모드
    if sys.argv[1] == "--batch":
        if len(sys.argv) < 3:
            print("❌ 설정 파일 경로를 지정하세요.")
            sys.exit(1)
        batch_process(sys.argv[2])
    
    # 단일 이미지 처리
    else:
        image_path = sys.argv[1]
        
        # 파일 존재 확인
        if not Path(image_path).exists():
            print(f"❌ 파일을 찾을 수 없습니다: {image_path}")
            sys.exit(1)
        
        # 좌표가 제공된 경우
        if len(sys.argv) >= 6:
            x = int(sys.argv[2])
            y = int(sys.argv[3])
            width = int(sys.argv[4])
            height = int(sys.argv[5])
            thickness = int(sys.argv[6]) if len(sys.argv) > 6 else 5
            
            add_red_border(image_path, x, y, width, height, thickness)
        
        # 대화형 모드
        else:
            add_red_border_interactive(image_path)
