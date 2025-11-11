export async function detectExpressionFromFrame({ apiBase, route, blob, room, size, signal }) {
  const fd = new FormData();
  fd.append("image", blob, "frame.jpg"); // <-- clave 'image'
  fd.append("room", room ?? "test");
  fd.append("size", String(size ?? 640)); // strings en form-data está OK

  const res = await fetch(`${apiBase}${route}`, {
    method: "POST",
    body: fd,
    signal,
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${txt}`);
  }

  const data = await res.json();
  return data;
}