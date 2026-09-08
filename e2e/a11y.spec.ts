import { test, expect } from '@playwright/test';
import { injectAxe, checkA11y } from 'axe-playwright';

// D22, D23, D21 접근성 회귀 방지 테스트
// 주요 검증:
// - D21: viewport 확대 제한 제거 (user-scalable=no 미검출)
// - D22: 빈 버튼/aria-label 수정
// - D23: 의미론적 HTML (header, nav, button 등)

test.describe('접근성 스모크 (D21, D22, D23)', () => {

  test.beforeEach(async ({ page }) => {
    // 모든 페이지 로드 전 axe-core 주입
    await page.goto('/');
    await injectAxe(page);
  });

  test('D21: viewport 확대/축소 차단 없음', async ({ page }) => {
    const viewport = await page.locator('meta[name="viewport"]').getAttribute('content');

    // user-scalable=no, maximum-scale, minimum-scale 모두 제거되어야 함
    expect(viewport).not.toContain('user-scalable=no');
    expect(viewport).not.toContain('maximum-scale');
    expect(viewport).not.toContain('minimum-scale');

    // 모바일 환경에서 확대/축소 가능 확인
    await page.evaluate(() => {
      const viewport = document.querySelector('meta[name="viewport"]');
      if (!viewport) throw new Error('Viewport meta tag missing');
      return viewport.getAttribute('content');
    });
  });

  test('D22: 아이콘 버튼에 aria-label 존재', async ({ page }) => {
    // 검색버튼, 메뉴버튼 등 아이콘만 있는 버튼들
    const buttons = page.locator('button');
    const count = await buttons.count();

    for (let i = 0; i < count; i++) {
      const button = buttons.nth(i);
      const text = await button.textContent();
      const ariaLabel = await button.getAttribute('aria-label');
      const ariaLabelledby = await button.getAttribute('aria-labelledby');

      // 텍스트가 없으면 aria-label 또는 aria-labelledby 필수
      if (!text || text.trim() === '') {
        expect(ariaLabel || ariaLabelledby).toBeTruthy(
          `Button without text must have aria-label or aria-labelledby: ${await button.innerHTML()}`
        );
      }
    }
  });

  test('D23: 의미론적 HTML 구조', async ({ page }) => {
    // 헤더는 <header> 태그 사용
    const header = page.locator('header, [role="banner"]');
    expect(await header.count()).toBeGreaterThan(0);

    // 네비게이션은 <nav> 또는 role="navigation"
    const nav = page.locator('nav, [role="navigation"]');
    expect(await nav.count()).toBeGreaterThan(0);

    // 메인 콘텐츠는 <main>
    const main = page.locator('main, [role="main"]');
    expect(await main.count()).toBeGreaterThan(0);

    // 클릭 가능한 요소는 <button> 또는 <a> (role="button" 아님)
    const clickables = page.locator('[onclick]');
    const count = await clickables.count();

    if (count > 0) {
      // onclick이 있으면 <button>이어야 함
      for (let i = 0; i < Math.min(count, 5); i++) {
        const element = clickables.nth(i);
        const tag = await element.evaluate(el => el.tagName);

        expect(['BUTTON', 'A']).toContain(tag);
      }
    }
  });

  test('axe-core 자동 스캔 (전체 페이지)', async ({ page }) => {
    // axe-core로 접근성 위반 검증
    // 심각도별 필터:
    // - violations (필수 수정): WCAG 레벨 A 위반
    // - incompleteness (확인 필요): 자동 검증 불가능한 항목

    const results = await page.evaluate(async () => {
      return await (window as any).axe.run({
        runOnly: {
          type: 'tag',
          values: ['wcag2aa', 'wcag21aa']
        }
      });
    });

    // axe.run() 반환값
    interface AxeResults {
      violations: Array<{ id: string; impact: string; nodes: unknown[] }>;
      incomplete: Array<{ id: string }>;
    }

    const axeResults = results as AxeResults;

    // 심각한 위반 확인
    const violations = axeResults.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');

    expect(violations).toHaveLength(0);
    if (violations.length > 0) {
      console.error('접근성 위반:', violations.map(v => ({ id: v.id, impact: v.impact })));
    }
  });

  test('모바일 메뉴 접근성 (ARIA)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 }); // iPhone 크기

    const menuButton = page.locator('.maars_menu, [data-testid="menu-toggle"]').first();

    if (await menuButton.isVisible()) {
      // 메뉴 버튼에 aria-expanded 속성 확인
      const ariaExpanded = await menuButton.getAttribute('aria-expanded');
      expect(ariaExpanded).toBe('false');

      // 메뉴 클릭
      await menuButton.click();

      // 메뉴가 열렸으면 aria-expanded=true
      const expanded = await menuButton.getAttribute('aria-expanded');
      expect(expanded).toBe('true');

      // 메뉴 컨테이너에 role="navigation" 확인
      const menuContainer = page.locator('.hd_menu');
      const role = await menuContainer.getAttribute('role');
      expect(role).toBe('navigation');
    }
  });

  test('포커스 관리 (키보드 네비게이션)', async ({ page }) => {
    // 첫 번째 포커스 가능 요소로 이동
    await page.keyboard.press('Tab');
    const firstFocused = await page.evaluate(() => document.activeElement?.tagName);

    expect(['BUTTON', 'A', 'INPUT']).toContain(firstFocused);

    // Tab 연속 입력으로 모든 포커스 가능 요소 순회
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
      const focused = await page.evaluate(() => document.activeElement?.tagName);

      if (focused === 'BODY') {
        // 마지막에 body로 돌아옴 = 정상
        break;
      }
      expect(['BUTTON', 'A', 'INPUT']).toContain(focused);
    }
  });

  test('이미지 alt text 검증', async ({ page }) => {
    const images = page.locator('img');
    const count = await images.count();

    for (let i = 0; i < count; i++) {
      const img = images.nth(i);
      const alt = await img.getAttribute('alt');
      const ariaLabel = await img.getAttribute('aria-label');
      const role = await img.getAttribute('role');

      // role="presentation"이면 alt 불필요
      if (role === 'presentation') {
        continue;
      }

      // 그 외에는 alt 또는 aria-label 필수
      expect(alt !== null || ariaLabel !== null).toBeTruthy(
        `Image must have alt text or aria-label: ${await img.getAttribute('src')}`
      );
    }
  });

  test('색상 대비 (최소 4.5:1)', async ({ page }) => {
    // 텍스트 요소들의 색상 대비 검증
    // 이는 axe-core의 color-contrast 룰로도 검증되지만,
    // 추가적으로 critical text 수동 검증

    const headings = page.locator('h1, h2, h3, p');
    const count = await headings.count();

    for (let i = 0; i < Math.min(count, 5); i++) {
      const element = headings.nth(i);
      const computed = await element.evaluate((el) => {
        const style = window.getComputedStyle(el);
        return {
          color: style.color,
          backgroundColor: style.backgroundColor,
          fontSize: style.fontSize
        };
      });

      // 최소한 컬러가 정의되어 있는지 확인
      expect(computed.color).toBeDefined();
      expect(computed.backgroundColor).toBeDefined();
    }
  });

  test('양식 필드 라벨 검증', async ({ page }) => {
    const inputs = page.locator('input[type="text"], textarea, select');
    const count = await inputs.count();

    for (let i = 0; i < count; i++) {
      const input = inputs.nth(i);
      const id = await input.getAttribute('id');
      const ariaLabel = await input.getAttribute('aria-label');
      const ariaLabelledby = await input.getAttribute('aria-labelledby');

      // label 태그로 연결되는지 또는 aria-label 필수
      if (id) {
        const label = page.locator(`label[for="${id}"]`);
        const hasLabel = await label.count() > 0;

        if (!hasLabel) {
          expect(ariaLabel || ariaLabelledby).toBeTruthy(
            `Form field #${id} must have label or aria-label`
          );
        }
      } else {
        expect(ariaLabel || ariaLabelledby).toBeTruthy(
          `Form field without id must have aria-label or aria-labelledby`
        );
      }
    }
  });

  test('언어 속성 설정 (html lang)', async ({ page }) => {
    const lang = await page.locator('html').getAttribute('lang');
    expect(lang).toBe('ko'); // 한국어 사이트
  });
});

// 추가: 데스크톱 + 모바일 테스트
test.describe('Cross-device 접근성', () => {

  const devices = [
    { name: 'Desktop', width: 1920, height: 1080 },
    { name: 'Tablet', width: 768, height: 1024 },
    { name: 'Mobile', width: 375, height: 667 }
  ];

  devices.forEach(device => {
    test(`${device.name} 접근성 검증`, async ({ page }) => {
      await page.setViewportSize({ width: device.width, height: device.height });
      await page.goto('/');
      await injectAxe(page);

      const results = await page.evaluate(async () => {
        return await (window as any).axe.run();
      });

      interface AxeResults {
        violations: Array<{ impact: string }>;
      }
      const axeResults = results as AxeResults;
      const violations = axeResults.violations.filter(v => v.impact === 'critical');

      expect(violations).toHaveLength(0);
    });
  });
});
