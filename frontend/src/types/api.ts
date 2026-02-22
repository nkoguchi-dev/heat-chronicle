export interface Prefecture {
  prec_no: number;
  name: string;
}

export interface Station {
  id: number;
  station_name: string;
  prec_no: number;
  block_no: string;
  station_type: string;
  latitude: number | null;
  longitude: number | null;
}

export interface TemperatureRecord {
  date: string;
  max_temp: number | null;
  min_temp: number | null;
  avg_temp: number | null;
}

export interface TemperatureMetadata {
  station_id: number;
  station_name: string;
  start_year: number;
  end_year: number;
  total_records: number;
  fetched_months: string[];
  fetching_required: boolean;
}

export interface TemperatureResponse {
  metadata: TemperatureMetadata;
  data: TemperatureRecord[];
}

export interface ProgressEvent {
  year: number;
  month: number;
  completed: number;
  total: number;
}

export interface DataEvent {
  year: number;
  month: number;
  records: TemperatureRecord[];
}

export interface CompleteEvent {
  message: string;
  total_records: number;
}

export interface ErrorEvent {
  message: string;
  year?: number;
  month?: number;
}

export type TempType = "max" | "min" | "avg";

export const TEMP_TYPE_LABELS: Record<TempType, string> = {
  max: "最高気温",
  min: "最低気温",
  avg: "平均気温",
};
