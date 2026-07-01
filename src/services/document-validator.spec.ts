/**
 * D09: 서류 검증 서비스 테스트
 * Week 1 Thursday: 4개 기본 테스트 케이스
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { validateDocument, validateDocuments } from './document-validator';

// Mock File 생성 헬퍼
const createMockFile = (
  name: string,
  type: string,
  size: number
): File => {
  const blob = new Blob(['x'.repeat(size)], { type });
  return new File([blob], name, { type });
};

describe('DocumentValidator', () => {

  describe('[T-D001] 유효한 서류 검증', () => {

    it('[T-D001] PDF 파일 검증 성공', async () => {
      const file = createMockFile('document.pdf', 'application/pdf', 1024 * 100);
      const result = await validateDocument({ file });

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
      expect(result.filename).toBe('document.pdf');
    });

    it('[T-D002] 이미지 파일 검증 성공 (JPEG)', async () => {
      const file = createMockFile('photo.jpg', 'image/jpeg', 1024 * 500);
      const result = await validateDocument({ file });

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('[T-D003] PNG 파일 검증 성공', async () => {
      const file = createMockFile('screenshot.png', 'image/png', 1024 * 200);
      const result = await validateDocument({ file });

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });
  });

  describe('[T-D004] 무효한 서류 거부', () => {

    it('[T-D004] 지원하지 않는 파일 타입 거부 (Word 문서)', async () => {
      const file = createMockFile('document.docx', 'application/msword', 1024 * 100);
      const result = await validateDocument({ file });

      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
      expect(result.errors[0]).toContain('not allowed');
    });

    it('[T-D005] 파일 크기 초과 거부 (51MB)', async () => {
      const file = createMockFile('large.pdf', 'application/pdf', 51 * 1024 * 1024);
      const result = await validateDocument({ file });

      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes('exceeds maximum'))).toBe(true);
    });

    it('[T-D006] 여러 파일 검증 (모두 유효)', async () => {
      const files = [
        createMockFile('doc1.pdf', 'application/pdf', 1024 * 100),
        createMockFile('photo.jpg', 'image/jpeg', 1024 * 200),
        createMockFile('screenshot.png', 'image/png', 1024 * 150)
      ];
      const result = await validateDocuments(files);

      expect(result.allValid).toBe(true);
      expect(result.validations).toHaveLength(3);
      expect(result.validations.every(v => v.valid)).toBe(true);
    });

    it('[T-D007] 여러 파일 중 일부 무효', async () => {
      const files = [
        createMockFile('doc1.pdf', 'application/pdf', 1024 * 100),
        createMockFile('invalid.txt', 'text/plain', 1024 * 50)
      ];
      const result = await validateDocuments(files);

      expect(result.allValid).toBe(false);
      expect(result.validations.some(v => !v.valid)).toBe(true);
    });
  });

});
