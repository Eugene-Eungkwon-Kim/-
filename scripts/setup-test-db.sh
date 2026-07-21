#!/bin/bash

# PostgreSQL 테스트 데이터베이스 설정 스크립트
#
# 사용: ./scripts/setup-test-db.sh
# 또는 환경변수로: PG_HOST=localhost PG_PORT=5432 PG_USER=postgres ./scripts/setup-test-db.sh

set -e

# 환경변수 설정 (기본값)
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-postgres}"
PG_TEST_DATABASE="${PG_TEST_DATABASE:-maars_test}"
PG_PASSWORD="${PG_PASSWORD:-}"

# PostgreSQL 연결 정보
if [ -z "$PG_PASSWORD" ]; then
  PSQL_CMD="psql -h $PG_HOST -p $PG_PORT -U $PG_USER"
else
  PSQL_CMD="PGPASSWORD=$PG_PASSWORD psql -h $PG_HOST -p $PG_PORT -U $PG_USER"
fi

echo "PostgreSQL 테스트 데이터베이스 설정 중..."
echo "Host: $PG_HOST"
echo "Port: $PG_PORT"
echo "User: $PG_USER"
echo "Database: $PG_TEST_DATABASE"

# 기존 테스트 DB 제거 (존재할 경우)
echo "기존 테스트 DB 제거 중..."
$PSQL_CMD -c "DROP DATABASE IF EXISTS $PG_TEST_DATABASE;" 2>/dev/null || true

# 새로운 테스트 DB 생성
echo "새로운 테스트 DB 생성 중..."
$PSQL_CMD -c "CREATE DATABASE $PG_TEST_DATABASE;"

echo "✓ 테스트 데이터베이스 설정 완료!"
echo ""
echo "다음 환경변수를 설정하고 테스트를 실행하세요:"
echo "export PG_HOST=$PG_HOST"
echo "export PG_PORT=$PG_PORT"
echo "export PG_USER=$PG_USER"
echo "export PG_PASSWORD='$PG_PASSWORD'"
echo "export PG_TEST_DATABASE=$PG_TEST_DATABASE"
echo ""
echo "npm test"
