export type TemperatureLoadMode = 'initial' | 'more';

export interface TemperatureLoadOperation {
  mode: TemperatureLoadMode;
  stationId: number;
  endYear: number;
}

export interface TemperatureLoadError {
  operation: TemperatureLoadOperation;
  message: string;
}
