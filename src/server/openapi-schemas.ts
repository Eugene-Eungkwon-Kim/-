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
  },

  // Phase 15 - Section 2/3
  Notification: {
    type: 'object',
    properties: {
      id: { type: 'string', format: 'uuid' },
      userId: { type: 'string', format: 'uuid' },
      metric: { type: 'string', enum: ['creditScore', 'financialHealthScore', 'riskScore', 'debtToIncomeRatio'] },
      severity: { type: 'string', enum: ['warning', 'critical', 'resolved'] },
      value: { type: 'number' },
      threshold: { type: 'number' },
      snapshotDate: { type: 'string', format: 'date' },
      readAt: { type: 'string', nullable: true },
      createdAt: { type: 'string' }
    }
  },
  MonthlyTrendPoint: {
    type: 'object',
    properties: {
      month: { type: 'string', description: 'YYYY-MM' },
      totalAmount: { type: 'number' },
      transactionCount: { type: 'integer' }
    }
  },
  TrendPoint: {
    type: 'object',
    properties: {
      date: { type: 'string', format: 'date' },
      value: { type: 'number' }
    }
  },
  PerformanceComparison: {
    type: 'object',
    properties: {
      metric: { type: 'string', enum: ['creditScore', 'financialHealthScore', 'riskScore', 'monthlySurplus'] },
      from: { $ref: '#/components/schemas/TrendPoint' },
      to: { $ref: '#/components/schemas/TrendPoint' },
      change: { type: 'number' },
      changePercent: { type: 'number' }
    }
  },
  ThresholdAlert: {
    type: 'object',
    properties: {
      metric: { type: 'string' },
      date: { type: 'string', format: 'date' },
      value: { type: 'number' },
      threshold: { type: 'number' },
      severity: { type: 'string', enum: ['warning', 'critical'] }
    }
  },
  FinancialSnapshotRecord: {
    type: 'object',
    properties: {
      id: { type: 'string', format: 'uuid' },
      userId: { type: 'string', format: 'uuid' },
      snapshotDate: { type: 'string', format: 'date' },
      creditScore: { type: 'number' },
      financialHealthScore: { type: 'number' },
      healthGrade: { type: 'string' },
      debtToIncomeRatio: { type: 'number' },
      assetToDebtRatio: { type: 'number' },
      monthlySurplus: { type: 'number' },
      riskScore: { type: 'number' },
      riskLevel: { type: 'string' },
      probabilityOfDefault: { type: 'number' },
      createdAt: { type: 'string' }
    }
  },
  TransactionSummary: {
    type: 'object',
    properties: {
      userId: { type: 'string', format: 'uuid' },
      transactionCount: { type: 'integer' },
      totalDeposits: { type: 'number' },
      totalWithdrawals: { type: 'number' },
      flaggedCount: { type: 'integer' },
      lastTransactionAt: { type: 'string', nullable: true }
    }
  },
  DashboardView: {
    type: 'object',
    properties: {
      summary: { $ref: '#/components/schemas/TransactionSummary', nullable: true },
      monthlyTrend: { type: 'array', items: { $ref: '#/components/schemas/MonthlyTrendPoint' } },
      latestSnapshot: { $ref: '#/components/schemas/FinancialSnapshotRecord', nullable: true },
      activeAlerts: { type: 'array', items: { $ref: '#/components/schemas/ThresholdAlert' } },
      degraded: { type: 'array', items: { type: 'string' }, description: '조합 중 실패해 낮춰진 필드 이름' }
    }
  }
};

/**
 * 응답 직렬화용 형태 정의 (Phase 15).
 *
 * response 스키마에는 '#/components/schemas/...' $ref를 쓸 수 없다. 그 참조는
 * @fastify/swagger가 문서를 그릴 때만 해석되고, 응답 직렬화를 담당하는
 * fast-json-stringify는 해석하지 못해 라우트 등록 자체가 실패한다
 * ("Cannot find reference"). 그래서 실제 객체를 참조로 재사용한다.
 *
 * 모든 정의에 additionalProperties: true를 둔다 — 선언에서 빠진 속성이 응답에서
 * 조용히 제거되는 것을 막기 위한 안전장치다.
 */
const errorShape = (description: string) =>
  ({
    description,
    type: 'object',
    additionalProperties: true,
    properties: {
      success: { const: false },
      error: {
        type: 'object',
        additionalProperties: true,
        properties: { code: { type: 'string' }, message: { type: 'string' } }
      }
    }
  }) as const;

const NOTIFICATION_SHAPE = {
  type: 'object',
  additionalProperties: true,
  properties: {
    id: { type: 'string' },
    userId: { type: 'string' },
    metric: { type: 'string' },
    severity: { type: 'string', enum: ['warning', 'critical', 'resolved'] },
    value: { type: 'number' },
    threshold: { type: 'number' },
    snapshotDate: { type: 'string' },
    readAt: { type: 'string', nullable: true },
    createdAt: { type: 'string' }
  }
} as const;

const MONTHLY_TREND_POINT_SHAPE = {
  type: 'object',
  additionalProperties: true,
  properties: {
    month: { type: 'string' },
    totalAmount: { type: 'number' },
    transactionCount: { type: 'integer' }
  }
} as const;

const TREND_POINT_SHAPE = {
  type: 'object',
  additionalProperties: true,
  properties: { date: { type: 'string' }, value: { type: 'number' } }
} as const;

const PERFORMANCE_COMPARISON_SHAPE = {
  type: 'object',
  additionalProperties: true,
  properties: {
    metric: { type: 'string' },
    from: TREND_POINT_SHAPE,
    to: TREND_POINT_SHAPE,
    change: { type: 'number' },
    changePercent: { type: 'number' }
  }
} as const;

const THRESHOLD_ALERT_SHAPE = {
  type: 'object',
  additionalProperties: true,
  properties: {
    metric: { type: 'string' },
    date: { type: 'string' },
    value: { type: 'number' },
    threshold: { type: 'number' },
    severity: { type: 'string', enum: ['warning', 'critical'] }
  }
} as const;

const AUDIT_LOG_ENTRY_SHAPE = {
  type: 'object',
  additionalProperties: true,
  properties: {
    id: { type: 'string' },
    entityType: { type: 'string' },
    entityId: { type: 'string' },
    action: { type: 'string' },
    actorId: { type: 'string', nullable: true },
    changes: { type: 'object', additionalProperties: true },
    occurredAt: { type: 'string' }
  }
} as const;

const DASHBOARD_VIEW_SHAPE = {
  type: 'object',
  additionalProperties: true,
  properties: {
    summary: { type: 'object', additionalProperties: true, nullable: true },
    monthlyTrend: { type: 'array', items: MONTHLY_TREND_POINT_SHAPE },
    latestSnapshot: { type: 'object', additionalProperties: true, nullable: true },
    activeAlerts: { type: 'array', items: THRESHOLD_ALERT_SHAPE },
    degraded: { type: 'array', items: { type: 'string' } }
  }
} as const;

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
  },

  // ---- Phase 15 - Section 3: 분석 API 노출 ----
  //
  // 주의: Fastify는 response 스키마로 응답을 직렬화하므로(fast-json-stringify),
  // 여기 선언하지 않은 속성은 응답에서 조용히 제거된다. 필드를 추가할 때는
  // 반드시 해당 라우트의 e2e 테스트가 그 필드를 단언하는지 함께 확인할 것.

  getTransactionTrend: {
    description: '거래 월별 추이 조회',
    tags: ['Transactions'],
    params: {
      type: 'object',
      properties: { userId: { type: 'string', format: 'uuid' } },
      required: ['userId']
    },
    response: {
      200: {
        description: '월별 추이 조회 성공',
        type: 'object',
        properties: {
          success: { const: true },
          data: { type: 'array', items: MONTHLY_TREND_POINT_SHAPE }
        }
      },
      403: errorShape('권한 없음')
    },
    security: [{ Bearer: [] }]
  },

  postSnapshotCompare: {
    description: '두 시점 스냅샷의 지표 변화 비교',
    tags: ['Analytics'],
    params: {
      type: 'object',
      properties: { userId: { type: 'string', format: 'uuid' } },
      required: ['userId']
    },
    body: {
      type: 'object',
      properties: {
        fromDate: { type: 'string', format: 'date' },
        toDate: { type: 'string', format: 'date' }
      },
      required: ['fromDate', 'toDate']
    },
    response: {
      200: {
        description: '비교 성공',
        type: 'object',
        properties: {
          success: { const: true },
          data: { type: 'array', items: PERFORMANCE_COMPARISON_SHAPE }
        }
      },
      403: errorShape('권한 없음'),
      404: errorShape('리소스를 찾을 수 없음')
    },
    security: [{ Bearer: [] }]
  },

  getTransactionAuditLog: {
    description: '거래 감사 로그 조회 (관리자 전용 — transactionId 생략 시 전체 거래)',
    tags: ['Admin'],
    querystring: {
      type: 'object',
      properties: {
        transactionId: { type: 'string' },
        from: { type: 'string', format: 'date' },
        to: { type: 'string', format: 'date' }
      }
    },
    response: {
      200: {
        description: '감사 로그 조회 성공',
        type: 'object',
        properties: {
          success: { const: true },
          data: { type: 'array', items: AUDIT_LOG_ENTRY_SHAPE }
        }
      },
      403: errorShape('권한 없음')
    },
    security: [{ Bearer: [] }]
  },

  getDashboard: {
    description: '대시보드 집계 (요약·추이·최신 스냅샷·활성 경고를 1회 요청으로)',
    tags: ['Analytics'],
    params: {
      type: 'object',
      properties: { userId: { type: 'string', format: 'uuid' } },
      required: ['userId']
    },
    response: {
      200: {
        description: '대시보드 조회 성공',
        type: 'object',
        properties: {
          success: { const: true },
          data: DASHBOARD_VIEW_SHAPE
        }
      },
      403: errorShape('권한 없음')
    },
    security: [{ Bearer: [] }]
  },

  // ---- Phase 15 - Section 2: 실시간 알림 ----

  getNotifications: {
    description: '알림 이력 조회',
    tags: ['Notifications'],
    params: {
      type: 'object',
      properties: { userId: { type: 'string', format: 'uuid' } },
      required: ['userId']
    },
    querystring: {
      type: 'object',
      properties: {
        unreadOnly: { type: 'string', enum: ['true', 'false'] },
        limit: { type: 'integer', minimum: 1 }
      }
    },
    response: {
      200: {
        description: '알림 조회 성공',
        type: 'object',
        properties: {
          success: { const: true },
          data: { type: 'array', items: NOTIFICATION_SHAPE }
        }
      },
      403: errorShape('권한 없음')
    },
    security: [{ Bearer: [] }]
  },

  postNotificationRead: {
    description: '알림 읽음 처리',
    tags: ['Notifications'],
    params: {
      type: 'object',
      properties: {
        userId: { type: 'string', format: 'uuid' },
        id: { type: 'string' }
      },
      required: ['userId', 'id']
    },
    response: {
      200: {
        description: '읽음 처리 성공',
        type: 'object',
        properties: {
          success: { const: true },
          data: NOTIFICATION_SHAPE
        }
      },
      403: errorShape('권한 없음'),
      404: errorShape('리소스를 찾을 수 없음')
    },
    security: [{ Bearer: [] }]
  },

  postNotificationTicket: {
    description: 'SSE 스트림용 1회용 티켓 발급 (EventSource가 Authorization 헤더를 설정할 수 없어 필요)',
    tags: ['Notifications'],
    response: {
      200: {
        description: '티켓 발급 성공',
        type: 'object',
        properties: {
          success: { const: true },
          data: {
            type: 'object',
            properties: {
              ticket: { type: 'string', format: 'uuid' },
              expiresInMs: { type: 'integer' }
            }
          }
        }
      },
      401: errorShape('인증 실패')
    },
    security: [{ Bearer: [] }]
  },

  // SSE는 reply.hijack()으로 Fastify의 응답 관리에서 빠져나가므로 response 스키마를
  // 선언하지 않는다 — 선언하면 직렬화 계층과 충돌한다. 문서화 목적의 메타데이터만 붙인다.
  getNotificationStream: {
    description:
      '알림 SSE 스트림. 티켓으로 인증하며(JWT 아님) text/event-stream을 반환한다. ' +
      '프레임: `event: connected` 1회 후 `event: notification` 다수, 25초마다 `: ping` 하트비트.',
    tags: ['Notifications'],
    // ticket을 required로 두거나 format: 'uuid'를 걸면 Fastify의 검증이 핸들러보다
    // 먼저 걸려 인증 실패가 401이 아니라 400으로 나간다. 티켓 유효성은 핸들러의
    // consumeTicket이 판단하므로 여기서는 문서화만 하고 검증하지 않는다.
    querystring: {
      type: 'object',
      properties: { ticket: { type: 'string', description: '1회용 SSE 티켓 (60초 만료)' } }
    },
    security: []
  }
};
