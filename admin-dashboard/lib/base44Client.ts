export const base44 = {
  rag: {
    upload: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("source", file.name);

      const res = await fetch("http://localhost:8000/rag/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Upload failed: ${res.status} - ${text}`);
      }

      return res.json(); // { status: "success", message: "xxx uploaded" }
    },

    getStats: async () => {
      const res = await fetch("http://localhost:8000/rag/stats");
      return res.json();
    },
    getRecent: async () => {
      const res = await fetch("http://localhost:8000/rag/recent");
      if (!res.ok) throw new Error("Failed to fetch recent updates");
      return res.json();
    },
    query: async ({ query, top_k = 5, threshold = 0.25 }) => {
      const res = await fetch("http://localhost:8000/rag/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query, top_k, threshold }),
      });

      if (!res.ok) throw new Error("RAG query failed");
      return res.json();
    },
  },
};
