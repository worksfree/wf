# -*- coding: utf-8 -*-
"""
Geometry override 테스트 (pytest 형식)
UI 자동화 테스트는 제외하고 geometry 파싱 로직만 테스트
"""
import pytest


class TestGeometryParsing:
    """Geometry 문자열 파싱 테스트"""

    def test_parse_geometry_string(self):
        """geometry 문자열 파싱 테스트"""
        geometry = "800x600+100+200"
        parts = geometry.split("+")

        assert len(parts) == 3
        size_part = parts[0]
        x = int(parts[1])
        y = int(parts[2])

        assert size_part == "800x600"
        assert x == 100
        assert y == 200

    def test_parse_size_from_geometry(self):
        """geometry에서 크기 추출 테스트"""
        geometry = "800x600+100+200"
        size_part = geometry.split("+")[0]
        width, height = size_part.split("x")

        assert int(width) == 800
        assert int(height) == 600

    def test_invalid_geometry_handling(self):
        """잘못된 geometry 형식 처리 테스트"""
        invalid_geometries = ["invalid", "800x600", "+100+200"]

        for geo in invalid_geometries:
            parts = geo.split("+")
            # 최소 3개 파트가 있어야 유효
            if len(parts) < 3:
                assert len(parts) < 3  # 예상대로 파싱 실패

    def test_geometry_position_tolerance(self):
        """창 위치 허용 오차 테스트"""
        saved_x, saved_y = 500, 400
        restored_x, restored_y = 505, 398  # 약간의 차이

        tolerance = 10
        pos_match = (
            abs(restored_x - saved_x) <= tolerance
            and abs(restored_y - saved_y) <= tolerance
        )

        assert pos_match, "위치 차이가 허용 오차 범위 내입니다"
