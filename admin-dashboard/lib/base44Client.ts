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
  },
};
