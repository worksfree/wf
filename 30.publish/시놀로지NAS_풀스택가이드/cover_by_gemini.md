---
title: "표지 - 시놀로지 NAS 풀스택 인프라 구축 완전 가이드"
author: "이인성"
lang: ko
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700;900&display=swap');

/* ── HTML 페이지 컨테이너 (표지·책소개·저자소개·판권) ── */
.html-page {
  width: 560px;
  height: 840px;
  overflow: hidden;
  page-break-after: always;
  break-after: page;
  position: relative;
}
/* ── 표지 CSS ── */
.cover {
  width: 560px;
  height: 840px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 20px 70px rgba(0,0,0,0.7);
  /* 추출된 전체 배경 이미지 */
  background: url('file:///d:/drive_files/10.worksfree/30.publish/시놀로지NAS_풀스택가이드/bg_0_X4.png') center top / cover no-repeat;
}
.network-layer {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  /* 원본 비율 960×703 → 560px 너비 기준 → 높이 410px */
  height: 410px;
  object-fit: cover;
  object-position: center bottom;
}
.text-layer {
  position: absolute;
  inset: 0;
}
.subtitle-top {
  position: absolute;
  top: 52px;
  left: 0; right: 0;
  text-align: center;
  font-size: 11px;
  font-weight: 300;
  color: rgba(255,255,255,0.55);
  letter-spacing: 2.5px;
  line-height: 2.1;
}
.title-block {
  position: absolute;
  top: 20%;
  left: 0; right: 0;
  text-align: center;
  padding: 0 20px;
}
.main-title {
  font-size: 60px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 6px;
  line-height: 1.05;
  margin-bottom: 16px;
  text-shadow: 0 2px 24px rgba(0,0,0,0.5);
}
.nas-en {
  font-family: 'Arial Black', Impact, Arial, sans-serif;
  font-weight: 900;
  letter-spacing: -1px;
}
.sub1 {
  font-size: 38px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 9px;
  line-height: 1.45;
  margin-bottom: 4px;
  text-shadow: 0 2px 20px rgba(0,0,0,0.5);
}
.sub2 {
  font-size: 38px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 9px;
  line-height: 1.45;
  text-shadow: 0 2px 20px rgba(0,0,0,0.5);
}
.bottom-block {
  position: absolute;
  bottom: 0;
  left: 0; right: 0;
  text-align: center;
  padding: 18px 0 52px;
  background: linear-gradient(0deg,
    rgba(4, 12, 28, 0.82) 0%,
    rgba(4, 12, 28, 0.60) 70%,
    rgba(4, 12, 28, 0) 100%
  );
}
.tagline {
  font-size: 12px;
  font-weight: 400;
  color: rgba(255,255,255,0.80);
  letter-spacing: 3px;
  margin-bottom: 10px;
}
.author-pub {
  font-size: 13px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 3px;
}
</style>

<div class="html-page">
<div class="cover">

  <!-- 네트워크 레이어 (텍스트 없는 순수 배경) -->
  <img class="network-layer" src="file:///d:/drive_files/10.worksfree/30.publish/시놀로지NAS_풀스택가이드/bg_1_X6.png" alt="">

  <!-- 텍스트 -->
  <div class="text-layer">

    <div class="subtitle-top">
      Cloudflare Tunnel부터<br>Supabase까지
    </div>

    <div class="title-block">
      <div class="main-title">시놀로지&ensp;<span class="nas-en">NAS</span></div>
      <div class="sub1">풀스택 인프라 구축</div>
      <div class="sub2">완전 가이드</div>
    </div>

    <div class="bottom-block">
      <div class="tagline">결제 연동, 배포 자동화까지</div>
      <div class="author-pub">이인성 저 &nbsp;·&nbsp; 웍스프리</div>
    </div>

  </div>
</div>
</div>
