import bootstrap from "@/data/bootstrap.json";

export const dynamic = "force-dynamic";

export async function GET() {
  const upstream = process.env.ATHMAR_STATE_URL;
  if (upstream) {
    try {
      const response = await fetch(upstream,{cache:"no-store",headers:{accept:"application/json"}});
      if (response.ok) return Response.json(await response.json(),{headers:{"cache-control":"no-store"}});
    } catch {}
  }
  return Response.json(bootstrap,{headers:{"cache-control":"no-store"}});
}
