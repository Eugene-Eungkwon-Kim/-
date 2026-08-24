import { Document, Packer, Paragraph, Table, TableCell, TableRow, WidthType, HeadingLevel, AlignmentType } from 'docx';
import fs from 'node:fs';

const doc = new Document({
  sections: [{
    properties: {},
    children: [
      // 제목
      new Paragraph({
        text: 'PostgreSQL 마이그레이션 - 애플리케이션 코드 전환',
        heading: HeadingLevel.HEADING_1,
        alignment: AlignmentType.CENTER,
        spacing: { after: 100 }
      }),
      new Paragraph({
        text: '기술 명세서 (Task M / N / O)',
        heading: HeadingLevel.HEADING_2,
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 }
      }),

      // 문서 정보
      new Paragraph({
        text: '문서 정보',
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 100, after: 100 }
      }),
      new Table({
        columnWidths: [2800, 5800],
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: '버전', bold: true })], width: { size: 2800, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '1.0' })], width: { size: 5800, type: WidthType.DXA } })
            ]
          }),
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: '작성일', bold: true })], width: { size: 2800, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '2026-07-21' })], width: { size: 5800, type: WidthType.DXA } })
            ]
          }),
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: '상태', bold: true })], width: { size: 2800, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '준비 완료 (승인 대기)' })], width: { size: 5800, type: WidthType.DXA } })
            ]
          }),
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: '선행 조건', bold: true })], width: { size: 2800, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: 'Day 15 Task J/K/L 완료' })], width: { size: 5800, type: WidthType.DXA } })
            ]
          })
        ]
      }),
      new Paragraph({ text: '' }),

      // 1. 개요
      new Paragraph({
        text: '1. 개요',
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 200, after: 100 }
      }),
      new Paragraph({
        text: '현재 MAARS 플랫폼은 SQLite 기반 동기식 데이터베이스 아키텍처를 사용하고 있습니다. Day 15 Tasks J/K/L을 통해 PostgreSQL 스키마 및 데이터 마이그레이션 준비가 완료되었습니다. 이제 애플리케이션 코드를 PostgreSQL 환경에 맞게 전환하는 단계입니다.',
        spacing: { after: 200 }
      }),

      new Paragraph({
        text: '목표',
        heading: HeadingLevel.HEADING_3,
        spacing: { before: 100, after: 50 }
      }),
      new Paragraph({
        text: '• better-sqlite3(동기) → pg(비동기) 드라이버 전환',
        spacing: { after: 50 }
      }),
      new Paragraph({
        text: '• SQLite 쿼리 문법 → PostgreSQL 표준 SQL로 통일',
        spacing: { after: 50 }
      }),
      new Paragraph({
        text: '• 파라미터 바인딩 방식 표준화 (? 또는 @name → $1, $2, ...)',
        spacing: { after: 50 }
      }),
      new Paragraph({
        text: '• 전체 리포지토리 계층의 async/await 패턴 도입',
        spacing: { after: 200 }
      }),

      // 2. Task M: 드라이버 교체
      new Paragraph({
        text: '2. Task M: 데이터베이스 드라이버 교체',
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 200, after: 100 }
      }),

      new Paragraph({
        text: '목표: better-sqlite3 제거, pg 라이브러리 도입',
        heading: HeadingLevel.HEADING_3,
        spacing: { before: 100, after: 100 }
      }),

      new Paragraph({
        text: '변경 사항',
        heading: HeadingLevel.HEADING_3,
        spacing: { before: 100, after: 50 }
      }),

      new Table({
        columnWidths: [1800, 3000, 3000],
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: '항목', bold: true })], width: { size: 1800, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '현재 (SQLite)', bold: true })], width: { size: 3000, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '변경 후 (PostgreSQL)', bold: true })], width: { size: 3000, type: WidthType.DXA } })
            ]
          }),
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: '라이브러리' })], width: { size: 1800, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: 'better-sqlite3' })], width: { size: 3000, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: 'pg (node-postgres)' })], width: { size: 3000, type: WidthType.DXA } })
            ]
          }),
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: '실행 모델' })], width: { size: 1800, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '동기식 (sync)' })], width: { size: 3000, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '비동기식 (Promise)' })], width: { size: 3000, type: WidthType.DXA } })
            ]
          }),
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: '연결 관리' })], width: { size: 1800, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '단일 DB 인스턴스' })], width: { size: 3000, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: 'Pool (다중 연결)' })], width: { size: 3000, type: WidthType.DXA } })
            ]
          }),
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: '트랜잭션' })], width: { size: 1800, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: 'db.transaction()' })], width: { size: 3000, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: 'BEGIN/COMMIT' })], width: { size: 3000, type: WidthType.DXA } })
            ]
          })
        ]
      }),
      new Paragraph({ text: '' }),

      // 3. Task N: 쿼리 방언 변환
      new Paragraph({
        text: '3. Task N: 쿼리 방언 변환',
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 200, after: 100 }
      }),

      new Paragraph({
        text: '목표: SQLite 특화 함수 → PostgreSQL 표준 SQL로 변환',
        heading: HeadingLevel.HEADING_3,
        spacing: { before: 100, after: 100 }
      }),

      new Paragraph({
        text: '주요 변환 규칙',
        heading: HeadingLevel.HEADING_3,
        spacing: { before: 100, after: 50 }
      }),

      new Table({
        columnWidths: [2000, 3400, 3400],
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: '항목', bold: true })], width: { size: 2000, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: 'SQLite', bold: true })], width: { size: 3400, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: 'PostgreSQL', bold: true })], width: { size: 3400, type: WidthType.DXA } })
            ]
          }),
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: 'JSON 추출' })], width: { size: 2000, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: "json_extract(col, '$.key')" })], width: { size: 3400, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: "(col->>'key')::jsonb" })], width: { size: 3400, type: WidthType.DXA } })
            ]
          }),
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: '파라미터' })], width: { size: 2000, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: "? 또는 @name" })], width: { size: 3400, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: "$1, $2, ..." })], width: { size: 3400, type: WidthType.DXA } })
            ]
          })
        ]
      }),
      new Paragraph({ text: '' }),

      // 4. Task O: 파라미터 바인딩
      new Paragraph({
        text: '4. Task O: 파라미터 바인딩 표준화',
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 200, after: 100 }
      }),

      new Paragraph({
        text: '목표: 모든 쿼리 파라미터를 PostgreSQL $1, $2, ... 형식으로 통일',
        heading: HeadingLevel.HEADING_3,
        spacing: { before: 100, after: 100 }
      }),

      // 5. 실행 계획
      new Paragraph({
        text: '5. 마이그레이션 실행 계획',
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 200, after: 100 }
      }),

      new Paragraph({
        text: '단계별 일정 (총 7-11일)',
        heading: HeadingLevel.HEADING_3,
        spacing: { before: 100, after: 50 }
      }),
      new Paragraph({
        text: '• Task M (드라이버 교체): 1-2일',
        spacing: { after: 30 }
      }),
      new Paragraph({
        text: '• Task N (쿼리 방언): 3-4일',
        spacing: { after: 30 }
      }),
      new Paragraph({
        text: '• Task O (파라미터): 1-2일',
        spacing: { after: 30 }
      }),
      new Paragraph({
        text: '• 통합 테스트: 2-3일',
        spacing: { after: 200 }
      }),

      // 6. 주요 리스크
      new Paragraph({
        text: '6. 위험도 및 완화 전략',
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 200, after: 100 }
      }),

      new Table({
        columnWidths: [1500, 2500, 3800],
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: '리스크', bold: true })], width: { size: 1500, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '심각도', bold: true })], width: { size: 2500, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '완화 전략', bold: true })], width: { size: 3800, type: WidthType.DXA } })
            ]
          }),
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: 'async 변환 누락' })], width: { size: 1500, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '높음' })], width: { size: 2500, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '체크리스트 + 코드 리뷰' })], width: { size: 3800, type: WidthType.DXA } })
            ]
          }),
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: '쿼리 문법 오류' })], width: { size: 1500, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '높음' })], width: { size: 2500, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: 'E2E 테스트 자동화' })], width: { size: 3800, type: WidthType.DXA } })
            ]
          }),
          new TableRow({
            cells: [
              new TableCell({ children: [new Paragraph({ text: 'PG 연결 실패' })], width: { size: 1500, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '중간' })], width: { size: 2500, type: WidthType.DXA } }),
              new TableCell({ children: [new Paragraph({ text: '환경 변수 검증' })], width: { size: 3800, type: WidthType.DXA } })
            ]
          })
        ]
      }),
      new Paragraph({ text: '' }),

      // 결론
      new Paragraph({
        text: '결론',
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 200, after: 100 }
      }),

      new Paragraph({
        text: '본 명세서는 PostgreSQL 마이그레이션 이후 애플리케이션 코드 계층의 전환을 위한 상세한 기술 계획입니다. Task M → N → O 순서로 진행하며, 각 단계별 테스트 및 코드 리뷰를 통해 품질을 보증합니다.',
        spacing: { after: 50 }
      })
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync('docs/PostgreSQL_Migration_Technical_Specification.docx', buffer);
  console.log('✅ 세부 명세서 생성 완료: docs/PostgreSQL_Migration_Technical_Specification.docx');
});
