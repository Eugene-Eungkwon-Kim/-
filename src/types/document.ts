/**
 * 서류 검증 관련 타입 정의
 */

export interface DocumentValidationInput {
  file: File;
}

export interface DocumentValidationResult {
  filename: string;
  valid: boolean;
  errors: string[];
}

export interface DocumentValidationResponse {
  allValid: boolean;
  validations: DocumentValidationResult[];
}

export const VALID_DOCUMENT_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/png'
];

export const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
export const MAX_TOTAL_SIZE = 500 * 1024 * 1024; // 500MB
