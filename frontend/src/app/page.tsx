"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/features/shared/libs/api-client";
import { HelloResponse } from "@/types/api";

export default function Home() {
  const [message, setMessage] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .get<HelloResponse>("/api/hello")
      .then((data) => setMessage(data.message))
      .catch((error) => setMessage(`Error: ${error.message}`))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <h1 className="text-4xl font-bold">
        {loading ? "Loading..." : message}
      </h1>
    </div>
  );
}
