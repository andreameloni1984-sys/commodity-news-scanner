// Sveglia dei bot: un Cloudflare Worker con timer (cron) ogni minuto che fa partire i
// workflow di GitHub Actions all'orario giusto. Le esecuzioni programmate di GitHub
// possono partire con 10-40 minuti di ritardo; quelle avviate da qui partono in 1-2 minuti.
// Le esecuzioni programmate di GitHub restano come riserva se la sveglia si ferma.
//
// Segreto richiesto nel Worker: GH_TOKEN (token GitHub "fine-grained" con permesso
// Actions: Read and write sui tre repository). Non scriverlo mai nel codice.

const OWNER = "andreameloni1984-sys";

// minute/hour/weekday in UTC. days: 1=lun ... 5=ven, 0=dom (come getUTCDay()).
const WEEKDAYS = [1, 2, 3, 4, 5];
const ALL_DAYS = [0, 1, 2, 3, 4, 5, 6];
const range = (a, b) => Array.from({ length: b - a + 1 }, (_, i) => a + i);

export const JOBS = [
  // Sputnik: post di Trump ogni 3 minuti, sempre
  { repo: "trump-trucker", workflow: "sputnik-fast.yml", every: 3, days: ALL_DAYS, hours: range(0, 23) },
  // Sputnik: giro completo (SEC, riepilogo delle 7:00, pagellino) ogni 15 minuti
  { repo: "trump-trucker", workflow: "trump_tracker.yml", minutes: [2, 17, 32, 47], days: ALL_DAYS, hours: range(0, 23) },
  // Sputnik demo (trader, PAC, trade Trump): ogni 5 minuti in orario di borsa europea
  { repo: "trump-trucker", workflow: "sputnik-demo-trader.yml", every: 5, days: WEEKDAYS, hours: range(7, 16) },
  // Gagarin: segnali CFD ogni 15 minuti (la riapertura della domenica sera inclusa)
  { repo: "commodity-news-scanner", workflow: "cfd-bot.yml", minutes: [1, 16, 31, 46], days: ALL_DAYS, hours: range(0, 23) },
  // Gagarin: bollettino delle 8:30 e "zona pericolosa" ogni 5 minuti nei giorni feriali
  { repo: "commodity-news-scanner", workflow: "cfd-briefing.yml", every: 5, days: WEEKDAYS, hours: range(6, 21) },
  // Stella Rossa: calendario dei dati USA ogni 10 minuti (resta acceso e controlla ogni 15 s vicino al dato)
  { repo: "agri-intelligence-bot", workflow: "oracle.yml", minutes: [3, 13, 23, 33, 43, 53], days: WEEKDAYS, hours: range(11, 21) },
  // Stella Rossa: scorte API del martedì sera (e mercoledì dopo le festività)
  { repo: "agri-intelligence-bot", workflow: "stella-api.yml", every: 5, days: [2, 3], hours: range(20, 23) },
  { repo: "agri-intelligence-bot", workflow: "stella-api.yml", every: 5, days: [3, 4], hours: [0, 1] },
];

export function due(job, date) {
  const m = date.getUTCMinutes();
  if (!job.days.includes(date.getUTCDay()) || !job.hours.includes(date.getUTCHours())) return false;
  return job.minutes ? job.minutes.includes(m) : m % job.every === 0;
}

async function dispatch(job, token) {
  const url = `https://api.github.com/repos/${OWNER}/${job.repo}/actions/workflows/${job.workflow}/dispatches`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "sveglia-bot",
    },
    body: JSON.stringify({ ref: "main" }),
  });
  return `${job.repo}/${job.workflow}: ${res.status}`;
}

export default {
  async scheduled(event, env) {
    if (!env.GH_TOKEN) {
      console.log("GH_TOKEN mancante: nessun workflow avviato");
      return;
    }
    const now = new Date(event.scheduledTime);
    const jobs = JOBS.filter((j) => due(j, now));
    const results = await Promise.all(jobs.map((j) => dispatch(j, env.GH_TOKEN).catch((e) => `${j.workflow}: ${e}`)));
    if (results.length) console.log(results.join(" | "));
  },

  // Visitando l'indirizzo del Worker si vede cosa partirebbe in questo minuto (nessun avvio).
  async fetch(request, env) {
    const now = new Date();
    const jobs = JOBS.filter((j) => due(j, now)).map((j) => `${j.repo}/${j.workflow}`);
    return new Response(
      `Sveglia bot attiva. Token configurato: ${env.GH_TOKEN ? "sì" : "NO"}\n` +
        `Ora UTC: ${now.toISOString()}\nIn programma in questo minuto: ${jobs.join(", ") || "niente"}\n`,
      { headers: { "content-type": "text/plain; charset=utf-8" } },
    );
  },
};
