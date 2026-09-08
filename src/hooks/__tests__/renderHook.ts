import { createElement, act as reactAct, type ReactElement } from 'react';
import { createRoot, type Root } from 'react-dom/client';

/**
 * 최소 renderHook (Phase 15 - B-2).
 *
 * 이 저장소에는 @testing-library가 설치돼 있지 않고, vitest는 .ts 스펙만 수집한다
 * (vitest.config.ts의 include). 훅 하나를 검증하려고 프론트엔드 테스트 인프라를
 * 통째로 들이는 대신, react-dom/client 위에 필요한 만큼만 만든다.
 * JSX를 쓰지 않으므로 .ts로 둘 수 있다.
 */

// React 19의 act는 이 플래그가 있어야 경고 없이 동작한다.
(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

export const act = reactAct;

export interface RenderHookResult<TResult, TProps> {
  result: { current: TResult };
  rerender: (props: TProps) => void;
  unmount: () => void;
}

export function renderHook<TResult, TProps extends object = Record<string, never>>(
  callback: (props: TProps) => TResult,
  options: { initialProps?: TProps } = {}
): RenderHookResult<TResult, TProps> {
  const result = { current: undefined as TResult };
  let currentProps = (options.initialProps ?? ({} as TProps)) as TProps;

  function Probe(props: TProps): ReactElement | null {
    result.current = callback(props);
    return null;
  }

  const container = document.createElement('div');
  document.body.appendChild(container);

  let root: Root;
  void reactAct(() => {
    root = createRoot(container);
    root.render(createElement(Probe, currentProps));
  });

  return {
    result,
    rerender: (props: TProps) => {
      currentProps = props;
      void reactAct(() => {
        root.render(createElement(Probe, currentProps));
      });
    },
    unmount: () => {
      void reactAct(() => {
        root.unmount();
      });
      container.remove();
    }
  };
}
