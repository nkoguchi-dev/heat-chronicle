'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { apiClient } from '@/features/shared/libs/api-client';
import type { Prefecture, Station } from '@/features/heatmap/types/api';

export type StationOptionsLoadPhase = 'prefectures' | 'stations';

export interface StationOptionsError {
  phase: StationOptionsLoadPhase;
  message: string;
}

interface UseStationOptionsParams {
  selectedPrecNo: number | null;
  initialStationId: number | null;
  onInitialStationResolved: (station: Station) => void;
}

interface UseStationOptionsReturn {
  prefectures: Prefecture[];
  stations: Station[];
  loadingPhase: StationOptionsLoadPhase | null;
  error: StationOptionsError | null;
  retry: () => void;
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

export function useStationOptions({
  selectedPrecNo,
  initialStationId,
  onInitialStationResolved,
}: UseStationOptionsParams): UseStationOptionsReturn {
  const [prefectures, setPrefectures] = useState<Prefecture[]>([]);
  const [stations, setStations] = useState<Station[]>([]);
  const [loadingPhase, setLoadingPhase] = useState<StationOptionsLoadPhase | null>('prefectures');
  const [error, setError] = useState<StationOptionsError | null>(null);
  const [prefecturesLoaded, setPrefecturesLoaded] = useState(false);

  const prefecturesControllerRef = useRef<AbortController | null>(null);
  const stationsControllerRef = useRef<AbortController | null>(null);
  const selectedPrecNoRef = useRef(selectedPrecNo);
  const initialStationIdRef = useRef(initialStationId);
  const onInitialStationResolvedRef = useRef(onInitialStationResolved);
  const initialStationResolvedRef = useRef(false);
  const lastRequestedPrecNoRef = useRef<number | null>(null);

  useEffect(() => {
    selectedPrecNoRef.current = selectedPrecNo;
  }, [selectedPrecNo]);

  useEffect(() => {
    onInitialStationResolvedRef.current = onInitialStationResolved;
  }, [onInitialStationResolved]);

  const loadStations = useCallback((precNo: number) => {
    stationsControllerRef.current?.abort();
    const controller = new AbortController();
    stationsControllerRef.current = controller;
    lastRequestedPrecNoRef.current = precNo;

    void Promise.resolve().then(async () => {
      if (controller.signal.aborted) return;
      setLoadingPhase('stations');
      setError(null);
      setStations([]);

      try {
        const data = await apiClient.get<Station[]>(`/api/stations?prec_no=${precNo}`, { signal: controller.signal });

        if (controller.signal.aborted || selectedPrecNoRef.current !== precNo) {
          return;
        }

        setStations(data);

        if (!initialStationResolvedRef.current) {
          initialStationResolvedRef.current = true;
          const station = data.find((candidate) => candidate.id === initialStationIdRef.current);
          if (station) {
            onInitialStationResolvedRef.current(station);
          }
        }

        setLoadingPhase(null);
      } catch (requestError) {
        if (isAbortError(requestError)) return;
        console.error('Failed to fetch stations:', requestError);
        if (selectedPrecNoRef.current === precNo) {
          setLoadingPhase(null);
          setError({
            phase: 'stations',
            message: '観測地点一覧を取得できませんでした。',
          });
        }
      }
    });
  }, []);

  const loadPrefectures = useCallback(() => {
    prefecturesControllerRef.current?.abort();
    const controller = new AbortController();
    prefecturesControllerRef.current = controller;

    void Promise.resolve().then(async () => {
      if (controller.signal.aborted) return;
      setLoadingPhase('prefectures');
      setError(null);

      try {
        const data = await apiClient.get<Prefecture[]>('/api/prefectures', {
          signal: controller.signal,
        });

        if (controller.signal.aborted) return;

        setPrefectures(data);
        setPrefecturesLoaded(true);

        const precNo = selectedPrecNoRef.current;
        if (precNo !== null) {
          loadStations(precNo);
        } else {
          setLoadingPhase(null);
        }
      } catch (requestError) {
        if (isAbortError(requestError)) return;
        console.error('Failed to fetch prefectures:', requestError);
        setLoadingPhase(null);
        setError({
          phase: 'prefectures',
          message: '都道府県一覧を取得できませんでした。',
        });
      }
    });
  }, [loadStations]);

  useEffect(() => {
    void loadPrefectures();

    return () => {
      prefecturesControllerRef.current?.abort();
      stationsControllerRef.current?.abort();
    };
  }, [loadPrefectures]);

  useEffect(() => {
    if (!prefecturesLoaded) return;

    if (selectedPrecNo === null) {
      stationsControllerRef.current?.abort();
      lastRequestedPrecNoRef.current = null;
      void Promise.resolve().then(() => {
        if (selectedPrecNoRef.current !== null) return;
        setStations([]);
        setLoadingPhase((current) => (current === 'stations' ? null : current));
      });
      return;
    }

    if (lastRequestedPrecNoRef.current !== selectedPrecNo) {
      void loadStations(selectedPrecNo);
    }
  }, [loadStations, prefecturesLoaded, selectedPrecNo]);

  const retry = useCallback(() => {
    if (error?.phase === 'prefectures') {
      void loadPrefectures();
      return;
    }

    const precNo = selectedPrecNoRef.current;
    if (precNo !== null) {
      void loadStations(precNo);
    }
  }, [error, loadPrefectures, loadStations]);

  return {
    prefectures,
    stations,
    loadingPhase,
    error,
    retry,
  };
}
