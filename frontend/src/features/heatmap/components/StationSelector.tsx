"use client";

import { useCallback, useRef, useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiClient } from "@/features/shared/libs/api-client";
import type { Prefecture, Station } from "@/types/api";

interface StationSelectorProps {
  prefectures: Prefecture[];
  selectedStationId: number | null;
  onSelect: (stationId: number) => void;
}

export function StationSelector({
  prefectures,
  selectedStationId,
  onSelect,
}: StationSelectorProps) {
  const [selectedPrecNo, setSelectedPrecNo] = useState<number | null>(null);
  const [stations, setStations] = useState<Station[]>([]);
  const [loadingStations, setLoadingStations] = useState(false);
  const fetchIdRef = useRef(0);

  const fetchStations = useCallback((precNo: number) => {
    const fetchId = ++fetchIdRef.current;
    setLoadingStations(true);
    setStations([]);
    apiClient
      .get<Station[]>(`/api/stations?prec_no=${precNo}`)
      .then((data) => {
        if (fetchIdRef.current === fetchId) {
          setStations(data);
          setLoadingStations(false);
        }
      })
      .catch((err) => {
        if (fetchIdRef.current === fetchId) {
          console.error(err);
          setLoadingStations(false);
        }
      });
  }, []);

  const handlePrefectureChange = (value: string) => {
    const precNo = Number(value);
    setSelectedPrecNo(precNo);
    fetchStations(precNo);
  };

  return (
    <div className="flex items-center gap-2">
      <Select
        value={selectedPrecNo?.toString() ?? ""}
        onValueChange={handlePrefectureChange}
      >
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="都道府県を選択" />
        </SelectTrigger>
        <SelectContent>
          {prefectures.map((pref) => (
            <SelectItem key={pref.prec_no} value={pref.prec_no.toString()}>
              {pref.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={selectedStationId?.toString() ?? ""}
        onValueChange={(value) => onSelect(Number(value))}
        disabled={selectedPrecNo === null || loadingStations}
      >
        <SelectTrigger className="w-[180px]">
          <SelectValue
            placeholder={loadingStations ? "読み込み中..." : "地点を選択"}
          />
        </SelectTrigger>
        <SelectContent>
          {stations.map((station) => (
            <SelectItem key={station.id} value={station.id.toString()}>
              {station.station_name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
