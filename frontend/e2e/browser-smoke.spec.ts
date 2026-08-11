import { expect, test, type Locator, type Page } from '@playwright/test';

import { browserSmokeYears, mockHeatChronicleApi } from './support/heat-chronicle-api';

const CELL_WIDTH = 3;
const CELL_HEIGHT = 12;
const LEFT_MARGIN = 50;
const TOP_MARGIN = 30;

test.beforeEach(async ({ context }) => {
  await mockHeatChronicleApi(context);
});

test('選択付きURLへ直接アクセスして再読み込みできる', async ({ page }) => {
  await page.goto('/?pref=44&station=4&type=min');
  await expectHeatmap(page, '大分県', '大分', '最低気温');

  await page.reload();
  await expectHeatmap(page, '大分県', '大分', '最低気温');
  await expect(page).toHaveURL(/\?pref=44&station=4&type=min$/);
});

test('キーボードで地点と気温種別を変更できる', async ({ page }) => {
  await page.goto('/?pref=44&station=4');
  await expectHeatmap(page, '大分県', '大分', '最高気温');

  const selectors = page.getByRole('combobox');
  await selectOptionWithKeyboard(page, selectors.nth(0), '東京都');
  const stationSelector = selectors.nth(1);
  await expect(stationSelector).toBeEnabled();
  await selectOptionWithKeyboard(page, stationSelector, '東京');
  await expectHeatmap(page, '東京都', '東京', '最高気温');
  await expect(page).toHaveURL(/\?pref=13&station=1$/);
  const canvas = page.getByRole('region', { name: '気温ヒートマップ' }).locator('canvas');
  const maximumTemperaturePixel = await readCanvasPixel(canvas, LEFT_MARGIN + 1, TOP_MARGIN + 1);

  const temperatureSelector = page.getByRole('combobox', { name: '気温種別' });
  await selectOptionWithKeyboard(page, temperatureSelector, '最低気温');
  await expect(page.getByText('日本の観測地点における最低気温の長期傾向ヒートマップ')).toBeVisible();
  await expect(page).toHaveURL(/type=min$/);
  const minimumTemperaturePixel = await readCanvasPixel(canvas, LEFT_MARGIN + 1, TOP_MARGIN + 1);
  expect(minimumTemperaturePixel).not.toEqual(maximumTemperaturePixel);

  await selectOptionWithKeyboard(page, temperatureSelector, '平均気温');
  await expect(page.getByText('日本の観測地点における平均気温の長期傾向ヒートマップ')).toBeVisible();
  await expect(page).toHaveURL(/type=avg$/);
  const averageTemperaturePixel = await readCanvasPixel(canvas, LEFT_MARGIN + 1, TOP_MARGIN + 1);
  expect(averageTemperaturePixel).not.toEqual(maximumTemperaturePixel);
  expect(averageTemperaturePixel).not.toEqual(minimumTemperaturePixel);
});

test('古い50年分を追加して表示済みデータを維持できる', async ({ page }) => {
  await page.goto('/?pref=44&station=4');
  const canvas = page.getByRole('region', { name: '気温ヒートマップ' }).locator('canvas');
  await expect(canvas).toBeVisible();

  const recentPixelBefore = await readCanvasPixel(canvas, LEFT_MARGIN + 1, TOP_MARGIN + 1);
  await page.getByRole('button', { name: `〜${browserSmokeYears.olderEnd}年のデータを読み込む` }).click();
  await expect(page.getByRole('button', { name: /年のデータを読み込む/ })).toHaveCount(0);

  const expectedHeight = TOP_MARGIN + 100 * CELL_HEIGHT;
  await expect.poll(() => canvas.evaluate((element) => (element as HTMLCanvasElement).height)).toBe(expectedHeight);
  const recentPixelAfter = await readCanvasPixel(canvas, LEFT_MARGIN + 1, TOP_MARGIN + 1);
  expect(recentPixelAfter).toEqual(recentPixelBefore);

  const oldestRow = TOP_MARGIN + 99 * CELL_HEIGHT + 1;
  const oldestRecordPixel = await readCanvasPixel(canvas, LEFT_MARGIN + 1, oldestRow);
  const oldestMissingPixel = await readCanvasPixel(canvas, LEFT_MARGIN + CELL_WIDTH + 1, oldestRow);
  expect(oldestRecordPixel).not.toEqual(oldestMissingPixel);
});

test('履歴の戻る・進む操作で気温種別を復元できる', async ({ page }) => {
  await page.goto('/?pref=44&station=4');
  await expectHeatmap(page, '大分県', '大分', '最高気温');
  const temperatureSelector = page.getByRole('combobox', { name: '気温種別' });

  await selectOptionWithKeyboard(page, temperatureSelector, '最低気温');
  await expect(page).toHaveURL(/type=min$/);
  await selectOptionWithKeyboard(page, temperatureSelector, '平均気温');
  await expect(page).toHaveURL(/type=avg$/);

  await page.goBack();
  await expectHeatmap(page, '大分県', '大分', '最低気温');
  await expect(page).toHaveURL(/type=min$/);
  await page.goBack();
  await expectHeatmap(page, '大分県', '大分', '最高気温');
  await expect(page).toHaveURL(/\?pref=44&station=4$/);

  await page.goForward();
  await expectHeatmap(page, '大分県', '大分', '最低気温');
  await page.goForward();
  await expectHeatmap(page, '大分県', '大分', '平均気温');
  await expect(page).toHaveURL(/type=avg$/);
});

async function expectHeatmap(page: Page, prefecture: string, station: string, temperatureType: string): Promise<void> {
  await expect(page.getByRole('heading', { name: 'Heat Chronicle' })).toBeVisible();
  const selectors = page.getByRole('combobox');
  await expect(selectors.nth(0)).toContainText(prefecture);
  await expect(selectors.nth(1)).toContainText(station);
  await expect(page.getByRole('combobox', { name: '気温種別' })).toContainText(temperatureType);
  await expect(page.getByText(`日本の観測地点における${temperatureType}の長期傾向ヒートマップ`)).toBeVisible();
  await expect(page.getByRole('region', { name: '気温ヒートマップ' })).toBeVisible();
  await expect(page.getByText('-10℃')).toBeVisible();
}

async function selectOptionWithKeyboard(page: Page, trigger: Locator, optionName: string): Promise<void> {
  await trigger.focus();
  await page.keyboard.press('Enter');
  const option = page.getByRole('option', { name: optionName });
  await expect(option).toBeVisible();
  await option.focus();
  await page.keyboard.press('Enter');
}

async function readCanvasPixel(
  canvas: Locator,
  horizontalPosition: number,
  verticalPosition: number,
): Promise<number[]> {
  return canvas.evaluate(
    (element, position) => {
      const context = (element as HTMLCanvasElement).getContext('2d');
      if (!context) throw new Error('Canvas 2D context is unavailable');
      return Array.from(context.getImageData(position.horizontal, position.vertical, 1, 1).data);
    },
    { horizontal: horizontalPosition, vertical: verticalPosition },
  );
}
