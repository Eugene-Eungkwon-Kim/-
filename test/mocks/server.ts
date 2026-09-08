import { setupServer } from 'msw/node';
import { loanHandlers } from './handlers';

export const server = setupServer(...loanHandlers);
