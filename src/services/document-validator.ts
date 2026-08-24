/**
 * 서류 검증 서비스
 * D09: 금융로직 단위테스트
 * 대출 신청 시 제출 서류의 형식 및 크기 검증
 */

import {
  DocumentValidationInput,
  DocumentValidationResult,
  DocumentValidationResponse,
  VALID_DOCUMENT_TYPES,
  MAX_FILE_SIZE,
  MAX_TOTAL_SIZE
} from '../types/document';

export async function validateDocument(input: DocumentValidationInput): Promise<DocumentValidationResult> {
  const errors: string[] = [];

  // 파일 존재 여부 확인
  if (!input.file) {
    errors.push('File is required');
    return {
      filename: 'unknown',
      valid: false,
      errors
    };
  }

  const { name, type, size } = input.file;

  // 파일명 확인
  if (!name || name.length === 0) {
    errors.push('Filename is required');
  }

  // 파일 크기 확인
  if (size > MAX_FILE_SIZE) {
    errors.push(`File size exceeds maximum of ${MAX_FILE_SIZE / 1024 / 1024}MB`);
  }

  // 파일 타입 확인
  if (!VALID_DOCUMENT_TYPES.includes(type)) {
    errors.push(`File type ${type} is not allowed. Allowed types: ${VALID_DOCUMENT_TYPES.join(', ')}`);
  }

  return {
    filename: name || 'unknown',
    valid: errors.length === 0,
    errors
  };
}

export async function validateDocuments(files: File[]): Promise<DocumentValidationResponse> {
  const validations: DocumentValidationResult[] = [];
  let totalSize = 0;

  // 파일 개수 확인
  if (!files || files.length === 0) {
    return {
      allValid: false,
      validations: [{
        filename: 'unknown',
        valid: false,
        errors: ['At least one file is required']
      }]
    };
  }

  // 각 파일 검증
  for (const file of files) {
    const result = await validateDocument({ file });
    validations.push(result);
    totalSize += file.size;
  }

  // 전체 용량 확인
  if (totalSize > MAX_TOTAL_SIZE) {
    return {
      allValid: false,
      validations: validations.map(v => ({
        ...v,
        errors: [...v.errors, `Total file size exceeds maximum of ${MAX_TOTAL_SIZE / 1024 / 1024}MB`]
      }))
    };
  }

  return {
    allValid: validations.every(v => v.valid),
    validations
  };
}
