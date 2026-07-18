/**
 * Day 14 - Task H (δ=400): OpenAPI 3.0 스키마 정의
 *
 * 모든 API 엔드포인트의 요청/응답 스키마를 중앙에서 관리한다.
 */

export const openAPISchemas = {
  // ============ 응답 구조 ============
  SuccessResponse: {
    type: 'object',
    properties: {
      success: { type: 'boolean', const: true },
      data: { type: 'object' }
    },
    required: ['success', 'data']
  },
  ErrorResponse: {
    type: 'object',
    properties: {
      success: { type: 'boolean', const: false },
      error: {
        type: 'object',
        properties: {
          code: { type: 'string' },
          message: { type: 'string' }
        },
        required: ['code', 'message']
      }
    },
    required: ['success', 'error']
  },

  // ============ 에러 타입 ============
  ValidationError: {
    type: 'object',
    properties: {
      success: { const: false },
      error: {
        type: 'object',
        properties: {
          code: { const: 'VALIDATION_ERROR' },
          message: { type: 'string' }
        }
      }
    }
  },
  DuplicateEmail: {
    type: 'object',
    properties: {
      success: { const: false },
      error: {
        type: 'object',
        properties: {
          code: { const: 'DUPLICATE_EMAIL' },
          message: { type: 'string' }
        }
      }
    }
  },
  NotFound: {
    type: 'object',
    properties: {
      success: { const: false },
      error: {
        type: 'object',
        properties: {
          code: { enum: ['USER_NOT_FOUND', 'LOAN_NOT_FOUND', 'TRANSACTION_NOT_FOUND', 'BACKUP_NOT_FOUND'] },
          message: { type: 'string' }
        }
      }
    }
  },
  Unauthorized: {
    type: 'object',
    properties: {
      success: { const: false },
      error: {
        type: 'object',
        properties: {
          code: { enum: ['INVALID_CREDENTIALS', 'INVALID_REFRESH_TOKEN'] },
          message: { type: 'string' }
        }
      }
    }
  },
  Forbidden: {
    type: 'object',
    properties: {
      success: { const: false },
      error: {
        type: 'object',
        properties: {
          code: { const: 'FORBIDDEN' },
          message: { type: 'string' }
        }
      }
    }
  },

  // ============ 도메인 모델 ============
  User: {
    type: 'object',
    properties: {
      id: { type: 'string', format: 'uuid' },
      email: { type: 'string', format: 'email' },
      name: { type: 'string', minLength: 1, maxLength: 100 },
      dateOfBirth: { type: 'string', format: 'date', nullable: true },
      employment: { $ref: '#/components/schemas/UserEmployment' },
      contact: { $ref: '#/components/schemas/UserContact' },
      creditProfile: { $ref: '#/components/schemas/CreditProfile' },
      financialSnapshot: { $ref: '#/components/schemas/FinancialSnapshot' },
      metadata: { $ref: '#/components/schemas/UserMetadata' }
    }
  },
  UserContact: {
    type: 'object',
    properties: {
      phone: { type: 'string', nullable: true },
      address: { $ref: '#/components/schemas/UserAddress' }
    }
  },
  UserAddress: {
    type: 'object',
    properties: {
      street: { type: 'string', nullable: true },
      city: { type: 'string', nullable: true },
      zipCode: { type: 'string', nullable: true },
      country: { type: 'string', nullable: true }
    }
  },
  UserEmployment: {
    type: 'object',
    properties: {
      status: { type: 'string', enum: ['employed', 'self-employed', 'unemployed', 'student'] },
      industry: { type: 'string', nullable: true },
      company: { type: 'string', nullable: true },
      tenure: { type: 'integer', nullable: true }
    }
  },
  UserMetadata: {
    type: 'object',
    properties: {
      version: { type: 'integer' },
      status: { type: 'string', enum: ['active', 'inactive', 'suspended'] },
      role: { type: 'string', enum: ['user', 'admin'] },
      createdAt: { type: 'string', format: 'date-time' },
      updatedAt: { type: 'string', format: 'date-time' },
      lastLoginAt: { type: 'string', format: 'date-time', nullable: true }
    }
  },
  CreditProfile: {
    type: 'object',
    properties: {
      score: { type: 'integer', minimum: 300, maximum: 850, nullable: true },
      grade: { type: 'string', enum: ['A', 'B', 'C', 'D', 'F'], nullable: true },
      inquiries: { type: 'integer', minimum: 0 },
      delinquency: { type: 'integer', minimum: 0 }
    }
  },
  FinancialSnapshot: {
    type: 'object',
    properties: {
      monthlyIncome: { type: 'number', nullable: true },
      monthlyExpenses: { type: 'number', nullable: true },
      totalAssets: { type: 'number', nullable: true },
      totalDebt: { type: 'number', nullable: true },
      savingsRate: { type: 'number', nullable: true }
    }
  },
  Loan: {
    type: 'object',
    properties: {
      id: { type: 'string', format: 'uuid' },
      userId: { type: 'string', format: 'uuid' },
      productId: { type: 'string' },
      originalAmount: { type: 'number', minimum: 1000 },
      currentBalance: { type: 'number', minimum: 0 },
      interestRate: { type: 'number', minimum: 0.5, maximum: 20 },
      termMonths: { type: 'integer', minimum: 12, maximum: 600 },
      status: { type: 'string', enum: ['active', 'repaid', 'defaulted'] },
      startDate: { type: 'string', format: 'date' },
      scheduledEndDate: { type: 'string', format: 'date' },
      nextPaymentDate: { type: 'string', format: 'date', nullable: true },
      createdAt: { type: 'string', format: 'date-time' }
    }
  },
  Transaction: {
    type: 'object',
    properties: {
      id: { type: 'string', format: 'uuid' },
      userId: { type: 'string', format: 'uuid' },
      transactionType: { type: 'string', enum: ['deposit', 'withdrawal', 'loan_payment', 'fee', 'adjustment'] },
      amount: { type: 'number', minimum: 0 },
      occurredAt: { type: 'string', format: 'date' },
      createdAt: { type: 'string', format: 'date-time' }
    }
  },
  AuditLog: {
    type: 'object',
    properties: {
      id: { type: 'string', format: 'uuid' },
      userId: { type: 'string', format: 'uuid' },
      action: { type: 'string', enum: ['CREATE', 'READ', 'UPDATE', 'DELETE', 'PAYMENT', 'LOAN_APPROVAL', 'LOGIN', 'LOGOUT'] },
      resourceType: { type: 'string' },
      resourceId: { type: 'string' },
      changesBefore: { type: 'object', nullable: true },
      changesAfter: { type: 'object', nullable: true },
      metadataIp: { type: 'string', nullable: true },
      status: { type: 'string', enum: ['success', 'failure'] },
      errorMessage: { type: 'string', nullable: true },
      createdAt: { type: 'string', format: 'date-time' }
    }
  },
  BackupRecord: {
    type: 'object',
    properties: {
      id: { type: 'string', format: 'uuid' },
      filename: { type: 'string' },
      size: { type: 'integer' },
      integrity: { type: 'string', enum: ['verified', 'pending', 'failed'] },
      createdAt: { type: 'string', format: 'date-time' },
      hash: { type: 'string' }
    }
  }
};

// 각 라우트의 스키마 설정
export const routeSchemas = {
  // 인증
  postUsers: {
    description: '사용자 회원가입',
    tags: ['Authentication'],
    body: {
      type: 'object',
      properties: {
        email: { type: 'string', format: 'email' },
        name: { type: 'string', minLength: 1, maxLength: 100 },
        password: { type: 'string', minLength: 8 },
        dateOfBirth: { type: 'string', format: 'date' },
        employment: {
          type: 'object',
          properties: {
            status: { type: 'string', enum: ['employed', 'self-employed', 'unemployed', 'student'] },
            industry: { type: 'string' },
            company: { type: 'string' },
            tenure: { type: 'integer' }
          }
        },
        contact: {
          type: 'object',
          properties: {
            phone: { type: 'string' },
            address: {
              type: 'object',
              properties: {
                street: { type: 'string' },
                city: { type: 'string' },
                zipCode: { type: 'string' },
                country: { type: 'string' }
              }
            }
          }
        },
        creditProfile: {
          type: 'object',
          properties: {
            score: { type: 'integer', minimum: 300, maximum: 850 }
          }
        },
        financialSnapshot: {
          type: 'object',
          properties: {
            monthlyIncome: { type: 'number' },
            monthlyExpenses: { type: 'number' },
            totalAssets: { type: 'number' },
            totalDebt: { type: 'number' },
            savingsRate: { type: 'number' }
          }
        }
      },
      required: ['email', 'name', 'password']
    },
    response: {
      200: {
        description: '회원가입 성공',
        type: 'object',
        additionalProperties: true
      },
      400: {
        description: '입력 검증 오류',
        type: 'object',
        additionalProperties: true
      },
      409: {
        description: '이메일 중복',
        type: 'object',
        additionalProperties: true
      }
    }
  },

  postLogin: {
    description: '사용자 로그인',
    tags: ['Authentication'],
    body: {
      type: 'object',
      properties: {
        email: { type: 'string', format: 'email' },
        password: { type: 'string', minLength: 8 }
      },
      required: ['email', 'password']
    },
    response: {
      200: {
        description: '로그인 성공',
        type: 'object',
        properties: {
          success: { const: true },
          data: {
            type: 'object',
            properties: {
              token: { type: 'string', description: 'JWT Access Token' },
              refreshToken: { type: 'string', description: 'Refresh Token' },
              user: { $ref: '#/components/schemas/User' }
            }
          }
        }
      },
      401: { $ref: '#/components/responses/Unauthorized' }
    }
  },

  postRefresh: {
    description: '액세스 토큰 갱신',
    tags: ['Authentication'],
    body: {
      type: 'object',
      properties: {
        refreshToken: { type: 'string' }
      },
      required: ['refreshToken']
    },
    response: {
      200: {
        description: '토큰 갱신 성공',
        type: 'object',
        properties: {
          success: { const: true },
          data: {
            type: 'object',
            properties: {
              token: { type: 'string' },
              refreshToken: { type: 'string' }
            }
          }
        }
      },
      401: { $ref: '#/components/responses/Unauthorized' }
    }
  },

  postLogout: {
    description: '사용자 로그아웃',
    tags: ['Authentication'],
    body: {
      type: 'object',
      properties: {
        refreshToken: { type: 'string' }
      },
      required: ['refreshToken']
    },
    response: {
      200: {
        description: '로그아웃 성공',
        type: 'object',
        properties: {
          success: { const: true },
          data: { type: 'object' }
        }
      }
    }
  },

  // 사용자 관리
  getUser: {
    description: '사용자 프로필 조회',
    tags: ['Users'],
    params: {
      type: 'object',
      properties: {
        userId: { type: 'string', format: 'uuid' }
      }
    },
    response: {
      200: {
        description: '프로필 조회 성공',
        type: 'object',
        properties: {
          success: { const: true },
          data: { $ref: '#/components/schemas/User' }
        }
      },
      404: { $ref: '#/components/responses/NotFound' }
    },
    security: [{ Bearer: [] }]
  },

  // 대출
  postLoan: {
    description: '대출 신청',
    tags: ['Loans'],
    body: {
      type: 'object',
      properties: {
        userId: { type: 'string', format: 'uuid' },
        productId: { type: 'string' },
        originalAmount: { type: 'number', minimum: 1000, maximum: 1000000000 },
        interestRate: { type: 'number', minimum: 0.5, maximum: 20 },
        termMonths: { type: 'integer', minimum: 12, maximum: 600 },
        startDate: { type: 'string', format: 'date' }
      },
      required: ['userId', 'productId', 'originalAmount', 'interestRate', 'termMonths', 'startDate']
    },
    response: {
      200: {
        description: '대출 신청 성공',
        type: 'object',
        properties: {
          success: { const: true },
          data: { $ref: '#/components/schemas/Loan' }
        }
      },
      400: { $ref: '#/components/responses/ValidationError' }
    },
    security: [{ Bearer: [] }]
  },

  // 거래
  postTransaction: {
    description: '거래 기록',
    tags: ['Transactions'],
    body: {
      type: 'object',
      properties: {
        userId: { type: 'string', format: 'uuid' },
        transactionType: { type: 'string', enum: ['deposit', 'withdrawal', 'loan_payment', 'fee', 'adjustment'] },
        amount: { type: 'number', minimum: 0.01, maximum: 10000000 },
        occurredAt: { type: 'string', format: 'date' }
      },
      required: ['userId', 'transactionType', 'amount', 'occurredAt']
    },
    response: {
      200: {
        description: '거래 기록 성공',
        type: 'object',
        properties: {
          success: { const: true },
          data: { $ref: '#/components/schemas/Transaction' }
        }
      },
      400: { $ref: '#/components/responses/ValidationError' }
    },
    security: [{ Bearer: [] }]
  },

  // 감사
  getAuditLogs: {
    description: '감사 로그 조회',
    tags: ['Audit'],
    querystring: {
      type: 'object',
      properties: {
        limit: { type: 'integer', default: 100 },
        offset: { type: 'integer', default: 0 },
        action: { type: 'string' },
        resourceType: { type: 'string' }
      }
    },
    response: {
      200: {
        description: '감사 로그 조회 성공',
        type: 'object',
        properties: {
          success: { const: true },
          data: {
            type: 'object',
            properties: {
              logs: {
                type: 'array',
                items: { $ref: '#/components/schemas/AuditLog' }
              },
              total: { type: 'integer' },
              limit: { type: 'integer' },
              offset: { type: 'integer' }
            }
          }
        }
      },
      403: { $ref: '#/components/responses/Forbidden' }
    },
    security: [{ Bearer: [] }]
  }
};
