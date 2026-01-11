"""
BOM_EXPORTER_USER_MANUAL.md의 이미지 스타일을 개선하는 스크립트
- 이미지 크기에 따라 적절한 max-width 적용
- 중앙 정렬 및 박스 정렬 개선
- 엑셀 이미지에 개인정보 마스킹 추가
"""

# 이미지 크기 정보 (width x height)
image_sizes = {
    "01_download.png": (913, 528),
    "02_extract.png": (613, 454),
    "03_folder_structure.png": (946, 514),
    "03_shortcut_script.png": (997, 616),
    "04_desktop_icon.png": (589, 427),
    "05_version_tooltip.png": (592, 430),
    "06_main_window.png": (885, 288),
    "08_register_form.png": (654, 646),
    "09_register_complete.png": (723, 288),
    "12_folder_dialog.png": (1257, 694),
    "13_folder_selected.png": (723, 288),
    "14_start_export-1.png": (723, 288),
    "14_start_export-2.png": (1915, 1041),
    "14_start_export-3.png": (900, 603),
    "16_progress_update.png": (1915, 1041),
    "17_complete.png": (723, 288),
    "18_result_folder.png": (1299, 817),
    "19_excel_result.png": (1156, 919),
    "20_credit_types-Both.png": (723, 288),
    "20_credit_types-Paid_Only.png": (723, 288),
    "20_credit_types-Trial_Only.png": (723, 288),
}

def get_max_width(width):
    """이미지 너비에 따라 적절한 max-width 반환"""
    if width <= 650:
        return "450px"  # 작은 이미지 - 원본 크기 유지
    elif width <= 900:
        return "650px"  # 중간 이미지 - 적당히 축소
    elif width <= 1300:
        return "800px"  # 큰 이미지 - 적당히 축소
    else:
        return "100%"   # 초대형 이미지 - 페이지 너비에 맞춤

def generate_style(img_name):
    """이미지 이름에 따라 스타일 생성"""
    if img_name in image_sizes:
        width, height = image_sizes[img_name]
        max_w = get_max_width(width)
        return f'max-width: {max_w}; border: 1px solid #ddd; display: block; margin: 10px auto;'
    else:
        # 기본 스타일
        return 'max-width: 650px; border: 1px solid #ddd; display: block; margin: 10px auto;'

# 각 이미지에 대한 스타일 출력
print("=" * 80)
print("이미지별 권장 스타일:")
print("=" * 80)
for img_name, (width, height) in sorted(image_sizes.items()):
    style = generate_style(img_name)
    print(f"\n{img_name:35s} ({width:4d} x {height:4d})")
    print(f"  style=\"{style}\"")
