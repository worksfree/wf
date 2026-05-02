import qrcode
from qrcode.constants import ERROR_CORRECT_L
from PIL import Image, ImageDraw, ImageFont

# URL을 최대한 짧게 (http/https 없이, www 없이)
url = "worksfree.com"

# QR 코드 생성 - 최소 복잡도
qr = qrcode.QRCode(
    version=1,  # 가장 작은 버전 (21x21 모듈)
    error_correction=ERROR_CORRECT_L,  # 가장 낮은 에러 정정 (7%) - 가장 단순
    box_size=25,  # 픽셀 크기 크게
    border=4,
)
qr.add_data(url)
qr.make(fit=True)
qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

print(f"QR 코드 버전: {qr.version}")
print(f"QR 코드 모듈 수: {qr.modules_count}x{qr.modules_count}")

# 폰트 설정
font_path_kr = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
font_path_en = "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"

font_title = ImageFont.truetype(font_path_kr, 48)
font_scan = ImageFont.truetype(font_path_en, 40)

# 텍스트 크기 계산
temp_draw = ImageDraw.Draw(qr_img)
title_text = "홈페이지"
scan_text = "Scan Me!"

title_bbox = temp_draw.textbbox((0, 0), title_text, font=font_title)
scan_bbox = temp_draw.textbbox((0, 0), scan_text, font=font_scan)

title_width = title_bbox[2] - title_bbox[0]
title_height = title_bbox[3] - title_bbox[1]
scan_width = scan_bbox[2] - scan_bbox[0]
scan_height = scan_bbox[3] - scan_bbox[1]

# 여백 및 간격 설정
qr_width, qr_height = qr_img.size
padding_top = 30
padding_bottom = 30
gap_top = 25
gap_bottom = 20
side_padding = 60

# 최종 캔버스 크기 계산
canvas_width = max(qr_width, title_width, scan_width) + side_padding * 2
canvas_height = padding_top + title_height + gap_top + qr_height + gap_bottom + scan_height + padding_bottom

# 새 캔버스 생성
canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
draw = ImageDraw.Draw(canvas)

# 상단 장식선
line_y = padding_top // 2
draw.line([(side_padding, line_y), (canvas_width - side_padding, line_y)], fill="#CCCCCC", width=2)

# "홈페이지" 텍스트
title_x = (canvas_width - title_width) // 2
title_y = padding_top
draw.text((title_x, title_y), title_text, font=font_title, fill="#333333")

# QR 코드 배치
qr_x = (canvas_width - qr_width) // 2
qr_y = padding_top + title_height + gap_top
canvas.paste(qr_img, (qr_x, qr_y))

# "Scan Me!" 텍스트
scan_x = (canvas_width - scan_width) // 2
scan_y = qr_y + qr_height + gap_bottom
draw.text((scan_x, scan_y), scan_text, font=font_scan, fill="#666666")

# 하단 장식선
bottom_line_y = canvas_height - padding_bottom // 2
draw.line([(side_padding, bottom_line_y), (canvas_width - side_padding, bottom_line_y)], fill="#CCCCCC", width=2)

# 저장
output_path = "/mnt/user-data/outputs/worksfree_qr_simple.png"
canvas.save(output_path, quality=95)

print(f"\nQR 코드 카드 생성 완료: {output_path}")
print(f"이미지 크기: {canvas.size[0]} x {canvas.size[1]} 픽셀")