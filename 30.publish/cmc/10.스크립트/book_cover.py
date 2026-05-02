import os
from cairosvg import svg2png

class SVGGenerator:
    def __init__(self, nth):
        self.nth = nth
        self.full_path = os.path.abspath(__file__)
        self.current_folder = os.getcwd()
        self.svg_code = self.create_svg_code()

    def create_svg_code(self):
        svg_code = f"""
<svg viewBox="0 0 600 850" xmlns="http://www.w3.org/2000/svg">
    <!-- 배경 -->
    <rect width="600" height="850" fill="#1a4a8f"/>
    <rect x="20" y="20" width="560" height="810" fill="#ffffff" rx="3"/>
    <rect x="200" y="800" width="200" height="80" fill="#ff6b3d" rx="30"/>
    <!-- 상단 강조 디자인 -->
    <path d="M0,0 L600,0 L600,120 L300,160 L0,120 Z" fill="#ff6b3d"/>
    <!-- 메인 타이틀 -->
    <text x="300" y="250" font-family="Malgun Gothic, Arial" font-size="48" font-weight="bold" text-anchor="middle" fill="#1a4a8f">
        경영지도사 2차 시험
    </text>
    <!-- 서브 타이틀 -->
    <text x="300" y="350" font-family="Malgun Gothic, Arial" font-size="72" font-weight="bold" text-anchor="middle" fill="#ff6b3d">
        생산관리분야
    </text>
    <!-- 회차 정보 -->
    <text x="300" y="450" font-family="Malgun Gothic, Arial" font-size="54" font-weight="bold" text-anchor="middle" fill="#1a4a8f">{self.nth}회 예시답안
    </text>
    <!-- 강조 아이콘 -->
    <circle cx="300" cy="600" r="80" fill="#f0f5ff"/>
    <text x="300" y="625" font-family="Malgun Gothic, Arial" font-size="90" font-weight="bold" text-anchor="middle" fill="#1a4a8f">
        A+
    </text>
    <!-- 저자 정보 -->
    <text x="300" y="760" font-family="Malgun Gothic, Arial" font-size="16" font-weight="bold" text-anchor="middle" fill="#1a4a8f">
        이인성 저
    </text>
    <!-- 장식 요소 -->
    <rect x="200" y="750" width="30" height="3" fill="#ff6b3d"/>
    <rect x="370" y="750" width="30" height="3" fill="#ff6b3d"/>
    <!-- 하단 설명 -->
    <text x="300" y="830" font-family="Malgun Gothic, Arial" font-size="16" font-weight="bold" text-anchor="middle" fill="#ffffff">
      유페이퍼
    </text>
</svg>
"""
        return svg_code

    def save_svg_as_png(self):
        filename = f'{self.full_path[:-3]}_{self.nth}.png'
        print(filename)
        svg2png(bytestring=self.svg_code, write_to=filename)

if __name__ == "__main__":
    nth = '37'  # 회차 정보
    svg_generator = SVGGenerator(nth)
    svg_generator.save_svg_as_png()