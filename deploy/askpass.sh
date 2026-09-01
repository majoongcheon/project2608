#!/usr/bin/env bash
# sudo 가 TTY 없이도 비밀번호를 받을 수 있게 하는 askpass 헬퍼.
#   SUDO_ASKPASS 규약: 비밀번호를 stdout 으로 한 줄 출력하면 sudo 가 읽어 간다.
#   입력값은 sudo 에게만 전달되며 파일·로그·환경변수 어디에도 남지 않는다.
osascript \
  -e 'display dialog "p3.sumzip.com nginx 설정을 설치합니다.\n\nmacOS 로그인 비밀번호(sudo)를 입력하세요." default answer "" with hidden answer buttons {"취소","확인"} default button "확인" with title "돌봄부담 진단 서비스 배포" with icon note' \
  -e 'text returned of result' 2>/dev/null
