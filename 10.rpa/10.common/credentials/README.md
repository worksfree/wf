# Google Sheets API Credentials

## 개발 환경 구조

```
10.common/
├── credentials/
│   ├── README.md                    # 이 파일
│   ├── google-service-account.json  # 실제 구글 서비스 계정 키 (gitignore)
│   └── google-service-account.json.template  # 템플릿 파일
└── wf_googlesheets_manager.py
```

## 배포 환경 구조

각 앱 배포 시:
```
app_folder/
├── res/
│   └── google-service-account.json  # PyInstaller로 번들링
└── app.exe
```

## 사용자 환경 구조

사용자 설치 후:
```
%USERPROFILE%/.wf_rpa/
├── credentials/
│   └── google-service-account.json  # 런타임에 복사/생성
├── .wf_rpa_config.json
└── .wf_app_policies.json
```

## 주의사항

1. **개발 환경**: `google-service-account.json`은 절대 git에 커밋하지 마세요
2. **배포 환경**: PyInstaller가 자동으로 각 앱에 포함시킵니다
3. **사용자 환경**: 앱 초기 실행시 자동으로 홈 폴더에 복사됩니다

## 사용법

1. Google Cloud Console에서 서비스 계정 키를 다운로드
2. `10.common/credentials/google-service-account.json`로 저장
3. `.spec` 파일이 자동으로 배포에 포함
4. 앱 실행시 사용자 홈에 자동 설치