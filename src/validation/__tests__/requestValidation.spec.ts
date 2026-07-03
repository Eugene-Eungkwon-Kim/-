import { describe, it, expect } from 'vitest';
import {
  ValidationError,
  validateUserRegistration,
  validateLogin,
  validateLoanApplication,
  validateLoanPayment,
  validateTransaction,
} from '../requestValidation';

describe('requestValidation', () => {
  describe('validateUserRegistration', () => {
    it('accepts valid registration input', () => {
      const valid = {
        name: 'John Doe',
        email: 'john@example.com',
        password: 'SecurePassword123',
        creditProfile: { score: 750 },
      };
      expect(() => validateUserRegistration(valid)).not.toThrow();
    });

    it('accepts valid input without creditProfile', () => {
      const valid = {
        name: 'Jane Smith',
        email: 'jane@example.com',
        password: 'SecurePass456',
      };
      expect(() => validateUserRegistration(valid)).not.toThrow();
    });

    it('accepts minimum valid name (1 char)', () => {
      const valid = {
        name: 'A',
        email: 'a@example.com',
        password: 'ValidPassword1',
      };
      expect(() => validateUserRegistration(valid)).not.toThrow();
    });

    it('accepts maximum valid name (100 chars)', () => {
      const valid = {
        name: 'A'.repeat(100),
        email: 'user@example.com',
        password: 'ValidPassword1',
      };
      expect(() => validateUserRegistration(valid)).not.toThrow();
    });

    it('rejects non-object input', () => {
      expect(() => validateUserRegistration('invalid')).toThrow(ValidationError);
      expect(() => validateUserRegistration(null)).toThrow(ValidationError);
      expect(() => validateUserRegistration(undefined)).toThrow(ValidationError);
      expect(() => validateUserRegistration(123)).toThrow(ValidationError);
    });

    it('rejects empty name', () => {
      const invalid = {
        name: '',
        email: 'user@example.com',
        password: 'ValidPassword1',
      };
      expect(() => validateUserRegistration(invalid)).toThrow(ValidationError);
    });

    it('rejects name exceeding 100 chars', () => {
      const invalid = {
        name: 'A'.repeat(101),
        email: 'user@example.com',
        password: 'ValidPassword1',
      };
      expect(() => validateUserRegistration(invalid)).toThrow(ValidationError);
    });

    it('rejects non-string name', () => {
      const invalid = {
        name: 123,
        email: 'user@example.com',
        password: 'ValidPassword1',
      };
      expect(() => validateUserRegistration(invalid)).toThrow(ValidationError);
    });

    it('rejects invalid email format', () => {
      const testCases = [
        { email: 'invalid' },
        { email: 'invalid@' },
        { email: '@example.com' },
        { email: 'user@.com' },
        { email: 'user@example' },
        { email: 'user @example.com' },
        { email: 'user@exam ple.com' },
      ];

      testCases.forEach(({ email }) => {
        const invalid = {
          name: 'User',
          email,
          password: 'ValidPassword1',
        };
        expect(() => validateUserRegistration(invalid)).toThrow(ValidationError);
      });
    });

    it('rejects non-string email', () => {
      const invalid = {
        name: 'User',
        email: 123,
        password: 'ValidPassword1',
      };
      expect(() => validateUserRegistration(invalid)).toThrow(ValidationError);
    });

    it('rejects password shorter than 8 chars', () => {
      const invalid = {
        name: 'User',
        email: 'user@example.com',
        password: 'Short1',
      };
      expect(() => validateUserRegistration(invalid)).toThrow(ValidationError);
    });

    it('rejects non-string password', () => {
      const invalid = {
        name: 'User',
        email: 'user@example.com',
        password: 12345678,
      };
      expect(() => validateUserRegistration(invalid)).toThrow(ValidationError);
    });

    it('accepts creditProfile.score at lower bound (300)', () => {
      const valid = {
        name: 'User',
        email: 'user@example.com',
        password: 'ValidPassword1',
        creditProfile: { score: 300 },
      };
      expect(() => validateUserRegistration(valid)).not.toThrow();
    });

    it('accepts creditProfile.score at upper bound (850)', () => {
      const valid = {
        name: 'User',
        email: 'user@example.com',
        password: 'ValidPassword1',
        creditProfile: { score: 850 },
      };
      expect(() => validateUserRegistration(valid)).not.toThrow();
    });

    it('rejects creditProfile.score below 300', () => {
      const invalid = {
        name: 'User',
        email: 'user@example.com',
        password: 'ValidPassword1',
        creditProfile: { score: 299 },
      };
      expect(() => validateUserRegistration(invalid)).toThrow(ValidationError);
    });

    it('rejects creditProfile.score above 850', () => {
      const invalid = {
        name: 'User',
        email: 'user@example.com',
        password: 'ValidPassword1',
        creditProfile: { score: 851 },
      };
      expect(() => validateUserRegistration(invalid)).toThrow(ValidationError);
    });

    it('rejects non-integer creditProfile.score', () => {
      const invalid = {
        name: 'User',
        email: 'user@example.com',
        password: 'ValidPassword1',
        creditProfile: { score: 750.5 },
      };
      expect(() => validateUserRegistration(invalid)).toThrow(ValidationError);
    });

    it('rejects non-object creditProfile', () => {
      const invalid = {
        name: 'User',
        email: 'user@example.com',
        password: 'ValidPassword1',
        creditProfile: 'invalid',
      };
      expect(() => validateUserRegistration(invalid)).toThrow(ValidationError);
    });
  });

  describe('validateLogin', () => {
    it('accepts valid login input', () => {
      const valid = {
        email: 'user@example.com',
        password: 'SecurePassword123',
      };
      expect(() => validateLogin(valid)).not.toThrow();
    });

    it('rejects non-object input', () => {
      expect(() => validateLogin('invalid')).toThrow(ValidationError);
      expect(() => validateLogin(null)).toThrow(ValidationError);
      expect(() => validateLogin(undefined)).toThrow(ValidationError);
    });

    it('rejects invalid email format', () => {
      const invalid = {
        email: 'invalid-email',
        password: 'ValidPassword1',
      };
      expect(() => validateLogin(invalid)).toThrow(ValidationError);
    });

    it('rejects password shorter than 8 chars', () => {
      const invalid = {
        email: 'user@example.com',
        password: 'Short',
      };
      expect(() => validateLogin(invalid)).toThrow(ValidationError);
    });

    it('rejects non-string password', () => {
      const invalid = {
        email: 'user@example.com',
        password: 12345678,
      };
      expect(() => validateLogin(invalid)).toThrow(ValidationError);
    });
  });

  describe('validateLoanApplication', () => {
    it('accepts valid loan application input', () => {
      const valid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 500000,
        interestRate: 5.5,
        termMonths: 60,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(valid)).not.toThrow();
    });

    it('rejects non-object input', () => {
      expect(() => validateLoanApplication('invalid')).toThrow(ValidationError);
      expect(() => validateLoanApplication(null)).toThrow(ValidationError);
    });

    it('rejects invalid UUID', () => {
      const invalid = {
        userId: 'not-a-uuid',
        originalAmount: 500000,
        interestRate: 5.5,
        termMonths: 60,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(invalid)).toThrow(ValidationError);
    });

    it('accepts valid UUID format', () => {
      const valid = {
        userId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
        originalAmount: 500000,
        interestRate: 5.5,
        termMonths: 60,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(valid)).not.toThrow();
    });

    it('rejects originalAmount below minimum (1000)', () => {
      const invalid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 999,
        interestRate: 5.5,
        termMonths: 60,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(invalid)).toThrow(ValidationError);
    });

    it('rejects originalAmount above maximum (1,000,000,000)', () => {
      const invalid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 1000000001,
        interestRate: 5.5,
        termMonths: 60,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(invalid)).toThrow(ValidationError);
    });

    it('accepts originalAmount at boundaries', () => {
      const minValid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 1000,
        interestRate: 5.5,
        termMonths: 60,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(minValid)).not.toThrow();

      const maxValid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 1000000000,
        interestRate: 5.5,
        termMonths: 60,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(maxValid)).not.toThrow();
    });

    it('rejects non-integer originalAmount', () => {
      const invalid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 500000.5,
        interestRate: 5.5,
        termMonths: 60,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(invalid)).toThrow(ValidationError);
    });

    it('rejects interestRate below minimum (0.5)', () => {
      const invalid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 500000,
        interestRate: 0.4,
        termMonths: 60,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(invalid)).toThrow(ValidationError);
    });

    it('rejects interestRate above maximum (20.0)', () => {
      const invalid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 500000,
        interestRate: 20.1,
        termMonths: 60,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(invalid)).toThrow(ValidationError);
    });

    it('accepts interestRate at boundaries', () => {
      const minValid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 500000,
        interestRate: 0.5,
        termMonths: 60,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(minValid)).not.toThrow();

      const maxValid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 500000,
        interestRate: 20.0,
        termMonths: 60,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(maxValid)).not.toThrow();
    });

    it('rejects termMonths below minimum (12)', () => {
      const invalid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 500000,
        interestRate: 5.5,
        termMonths: 11,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(invalid)).toThrow(ValidationError);
    });

    it('rejects termMonths above maximum (600)', () => {
      const invalid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 500000,
        interestRate: 5.5,
        termMonths: 601,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(invalid)).toThrow(ValidationError);
    });

    it('rejects non-integer termMonths', () => {
      const invalid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 500000,
        interestRate: 5.5,
        termMonths: 60.5,
        productId: 'PRODUCT_001',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(invalid)).toThrow(ValidationError);
    });

    it('rejects empty productId', () => {
      const invalid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 500000,
        interestRate: 5.5,
        termMonths: 60,
        productId: '',
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(invalid)).toThrow(ValidationError);
    });

    it('rejects non-string productId', () => {
      const invalid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 500000,
        interestRate: 5.5,
        termMonths: 60,
        productId: 123,
        startDate: '2025-01-15',
      };
      expect(() => validateLoanApplication(invalid)).toThrow(ValidationError);
    });

    it('rejects invalid ISO 8601 date', () => {
      const invalid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 500000,
        interestRate: 5.5,
        termMonths: 60,
        productId: 'PRODUCT_001',
        startDate: 'invalid-date',
      };
      expect(() => validateLoanApplication(invalid)).toThrow(ValidationError);
    });

    it('accepts valid ISO 8601 date', () => {
      const valid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        originalAmount: 500000,
        interestRate: 5.5,
        termMonths: 60,
        productId: 'PRODUCT_001',
        startDate: '2025-12-31',
      };
      expect(() => validateLoanApplication(valid)).not.toThrow();
    });
  });

  describe('validateLoanPayment', () => {
    it('accepts valid loan payment input', () => {
      const valid = {
        principal: 5000,
        interest: 250,
        fees: 50,
        paymentDate: '2025-01-15',
      };
      expect(() => validateLoanPayment(valid)).not.toThrow();
    });

    it('accepts valid payment without fees', () => {
      const valid = {
        principal: 5000,
        interest: 250,
        paymentDate: '2025-01-15',
      };
      expect(() => validateLoanPayment(valid)).not.toThrow();
    });

    it('rejects non-object input', () => {
      expect(() => validateLoanPayment('invalid')).toThrow(ValidationError);
      expect(() => validateLoanPayment(null)).toThrow(ValidationError);
    });

    it('rejects zero or negative principal', () => {
      const zeroTest = {
        principal: 0,
        interest: 250,
        paymentDate: '2025-01-15',
      };
      expect(() => validateLoanPayment(zeroTest)).toThrow(ValidationError);

      const negativeTest = {
        principal: -1000,
        interest: 250,
        paymentDate: '2025-01-15',
      };
      expect(() => validateLoanPayment(negativeTest)).toThrow(ValidationError);
    });

    it('accepts positive principal', () => {
      const valid = {
        principal: 0.01,
        interest: 0,
        paymentDate: '2025-01-15',
      };
      expect(() => validateLoanPayment(valid)).not.toThrow();
    });

    it('rejects negative interest', () => {
      const invalid = {
        principal: 5000,
        interest: -100,
        paymentDate: '2025-01-15',
      };
      expect(() => validateLoanPayment(invalid)).toThrow(ValidationError);
    });

    it('accepts zero interest', () => {
      const valid = {
        principal: 5000,
        interest: 0,
        paymentDate: '2025-01-15',
      };
      expect(() => validateLoanPayment(valid)).not.toThrow();
    });

    it('rejects negative fees', () => {
      const invalid = {
        principal: 5000,
        interest: 250,
        fees: -50,
        paymentDate: '2025-01-15',
      };
      expect(() => validateLoanPayment(invalid)).toThrow(ValidationError);
    });

    it('accepts zero fees', () => {
      const valid = {
        principal: 5000,
        interest: 250,
        fees: 0,
        paymentDate: '2025-01-15',
      };
      expect(() => validateLoanPayment(valid)).not.toThrow();
    });

    it('rejects future payment date', () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const futureDate = tomorrow.toISOString().split('T')[0];

      const invalid = {
        principal: 5000,
        interest: 250,
        paymentDate: futureDate,
      };
      expect(() => validateLoanPayment(invalid)).toThrow(ValidationError);
    });

    it('accepts today as payment date', () => {
      const today = new Date();
      const todayDate = today.toISOString().split('T')[0];

      const valid = {
        principal: 5000,
        interest: 250,
        paymentDate: todayDate,
      };
      expect(() => validateLoanPayment(valid)).not.toThrow();
    });

    it('accepts past payment date', () => {
      const valid = {
        principal: 5000,
        interest: 250,
        paymentDate: '2024-01-01',
      };
      expect(() => validateLoanPayment(valid)).not.toThrow();
    });
  });

  describe('validateTransaction', () => {
    it('accepts valid transaction input', () => {
      const valid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        transactionType: 'deposit',
        amount: 5000,
        occurredAt: '2025-01-15',
      };
      expect(() => validateTransaction(valid)).not.toThrow();
    });

    it('rejects non-object input', () => {
      expect(() => validateTransaction('invalid')).toThrow(ValidationError);
      expect(() => validateTransaction(null)).toThrow(ValidationError);
    });

    it('rejects invalid UUID', () => {
      const invalid = {
        userId: 'not-a-uuid',
        transactionType: 'deposit',
        amount: 5000,
        occurredAt: '2025-01-15',
      };
      expect(() => validateTransaction(invalid)).toThrow(ValidationError);
    });

    it('accepts all valid transaction types', () => {
      const types = ['deposit', 'withdrawal', 'loan_payment', 'fee', 'adjustment'];
      types.forEach((type) => {
        const valid = {
          userId: '550e8400-e29b-41d4-a716-446655440000',
          transactionType: type,
          amount: 5000,
          occurredAt: '2025-01-15',
        };
        expect(() => validateTransaction(valid)).not.toThrow();
      });
    });

    it('rejects invalid transaction type', () => {
      const invalid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        transactionType: 'invalid_type',
        amount: 5000,
        occurredAt: '2025-01-15',
      };
      expect(() => validateTransaction(invalid)).toThrow(ValidationError);
    });

    it('rejects zero or negative amount', () => {
      const zeroTest = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        transactionType: 'deposit',
        amount: 0,
        occurredAt: '2025-01-15',
      };
      expect(() => validateTransaction(zeroTest)).toThrow(ValidationError);

      const negativeTest = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        transactionType: 'deposit',
        amount: -1000,
        occurredAt: '2025-01-15',
      };
      expect(() => validateTransaction(negativeTest)).toThrow(ValidationError);
    });

    it('rejects amount exceeding maximum (10,000,000)', () => {
      const invalid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        transactionType: 'deposit',
        amount: 10000001,
        occurredAt: '2025-01-15',
      };
      expect(() => validateTransaction(invalid)).toThrow(ValidationError);
    });

    it('accepts amount at maximum (10,000,000)', () => {
      const valid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        transactionType: 'deposit',
        amount: 10000000,
        occurredAt: '2025-01-15',
      };
      expect(() => validateTransaction(valid)).not.toThrow();
    });

    it('accepts small positive amount', () => {
      const valid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        transactionType: 'deposit',
        amount: 0.01,
        occurredAt: '2025-01-15',
      };
      expect(() => validateTransaction(valid)).not.toThrow();
    });

    it('rejects future occurrence date', () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const futureDate = tomorrow.toISOString().split('T')[0];

      const invalid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        transactionType: 'deposit',
        amount: 5000,
        occurredAt: futureDate,
      };
      expect(() => validateTransaction(invalid)).toThrow(ValidationError);
    });

    it('accepts today as occurrence date', () => {
      const today = new Date();
      const todayDate = today.toISOString().split('T')[0];

      const valid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        transactionType: 'deposit',
        amount: 5000,
        occurredAt: todayDate,
      };
      expect(() => validateTransaction(valid)).not.toThrow();
    });

    it('accepts past occurrence date', () => {
      const valid = {
        userId: '550e8400-e29b-41d4-a716-446655440000',
        transactionType: 'withdrawal',
        amount: 5000,
        occurredAt: '2024-01-01',
      };
      expect(() => validateTransaction(valid)).not.toThrow();
    });
  });
});
