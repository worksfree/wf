import React from 'react';

export default function PlatformDiagram() {
  return (
    <div className="min-h-screen bg-slate-50 p-8 flex items-center justify-center">
      <div className="max-w-4xl w-full">
        {/* 타이틀 */}
        <h1 className="text-2xl font-bold text-center text-slate-800 mb-8">
          기계원리 콘텐츠 검색 플랫폼
        </h1>
        
        {/* 메인 플로우 */}
        <div className="relative">
          {/* 사용자 */}
          <div className="flex items-center justify-center mb-6">
            <div className="bg-blue-600 text-white px-6 py-4 rounded-xl shadow-lg flex items-center gap-3">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span className="font-semibold text-lg">자동화장비 설계자</span>
            </div>
          </div>
          
          {/* 화살표 */}
          <div className="flex justify-center mb-4">
            <svg className="w-6 h-10 text-slate-400" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" transform="rotate(90 12 12)"/>
            </svg>
          </div>
          
          {/* 검색 단계 */}
          <div className="bg-white rounded-2xl shadow-lg p-6 mb-4 border-2 border-amber-400">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-amber-400 text-white w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg">1</div>
              <h2 className="text-xl font-bold text-slate-800">키워드 / 텍스트 검색</h2>
            </div>
            <div className="bg-slate-100 rounded-lg p-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <span className="text-slate-600">"캠 메커니즘", "링크 구조", "기어 감속" ...</span>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="bg-amber-100 text-amber-700 px-3 py-1 rounded-full text-sm">직선운동</span>
              <span className="bg-amber-100 text-amber-700 px-3 py-1 rounded-full text-sm">회전운동</span>
              <span className="bg-amber-100 text-amber-700 px-3 py-1 rounded-full text-sm">간헐운동</span>
              <span className="bg-amber-100 text-amber-700 px-3 py-1 rounded-full text-sm">왕복운동</span>
            </div>
          </div>
          
          {/* 화살표 */}
          <div className="flex justify-center mb-4">
            <svg className="w-6 h-10 text-slate-400" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" transform="rotate(90 12 12)"/>
            </svg>
          </div>
          
          {/* 필터링 단계 */}
          <div className="bg-white rounded-2xl shadow-lg p-6 mb-4 border-2 border-emerald-400">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-emerald-500 text-white w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg">2</div>
              <h2 className="text-xl font-bold text-slate-800">동영상 필터링 & 미리보기</h2>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-slate-800 rounded-lg aspect-video flex items-center justify-center relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/20 to-transparent"></div>
                  <svg className="w-10 h-10 text-white/80" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z"/>
                  </svg>
                  <span className="absolute bottom-1 right-2 text-white/70 text-xs">0:3{i}</span>
                </div>
              ))}
            </div>
            <p className="text-slate-500 text-sm mt-3 text-center">작동 원리를 동영상으로 확인 후 선택</p>
          </div>
          
          {/* 화살표 */}
          <div className="flex justify-center mb-4">
            <svg className="w-6 h-10 text-slate-400" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" transform="rotate(90 12 12)"/>
            </svg>
          </div>
          
          {/* 다운로드 단계 */}
          <div className="bg-white rounded-2xl shadow-lg p-6 mb-4 border-2 border-violet-400">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-violet-500 text-white w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg">3</div>
              <h2 className="text-xl font-bold text-slate-800">3D CAD 모델 다운로드</h2>
            </div>
            <div className="flex justify-center gap-4">
              <div className="bg-violet-50 rounded-xl p-4 flex flex-col items-center gap-2">
                <div className="w-16 h-16 bg-violet-100 rounded-lg flex items-center justify-center">
                  <span className="text-violet-600 font-bold text-sm">.SLDPRT</span>
                </div>
                <span className="text-slate-600 text-sm">SolidWorks</span>
              </div>
              <div className="bg-violet-50 rounded-xl p-4 flex flex-col items-center gap-2">
                <div className="w-16 h-16 bg-violet-100 rounded-lg flex items-center justify-center">
                  <span className="text-violet-600 font-bold text-sm">.STEP</span>
                </div>
                <span className="text-slate-600 text-sm">범용 포맷</span>
              </div>
              <div className="bg-violet-50 rounded-xl p-4 flex flex-col items-center gap-2">
                <div className="w-16 h-16 bg-violet-100 rounded-lg flex items-center justify-center">
                  <span className="text-violet-600 font-bold text-sm">.IGS</span>
                </div>
                <span className="text-slate-600 text-sm">IGES</span>
              </div>
            </div>
          </div>
          
          {/* 화살표 */}
          <div className="flex justify-center mb-4">
            <svg className="w-6 h-10 text-slate-400" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" transform="rotate(90 12 12)"/>
            </svg>
          </div>
          
          {/* 결과 */}
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl shadow-lg p-6 text-white">
            <div className="flex items-center justify-center gap-3">
              <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <div>
                <h2 className="text-2xl font-bold">설계 시간 단축</h2>
                <p className="text-blue-100">기계원리 학습 + 3D 모델 활용 → 생산성 향상</p>
              </div>
            </div>
          </div>
        </div>
        
        {/* 핵심 가치 */}
        <div className="mt-8 grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl p-4 shadow text-center">
            <div className="text-3xl mb-2">🔍</div>
            <h3 className="font-semibold text-slate-800">빠른 검색</h3>
            <p className="text-slate-500 text-sm">키워드 기반 즉시 탐색</p>
          </div>
          <div className="bg-white rounded-xl p-4 shadow text-center">
            <div className="text-3xl mb-2">🎬</div>
            <h3 className="font-semibold text-slate-800">시각적 이해</h3>
            <p className="text-slate-500 text-sm">동영상으로 원리 파악</p>
          </div>
          <div className="bg-white rounded-xl p-4 shadow text-center">
            <div className="text-3xl mb-2">📦</div>
            <h3 className="font-semibold text-slate-800">즉시 활용</h3>
            <p className="text-slate-500 text-sm">CAD 파일 바로 적용</p>
          </div>
        </div>
      </div>
    </div>
  );
}
