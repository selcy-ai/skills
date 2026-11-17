# Dokploy + Traefik — deploy reference

Depth file for `/selcy-deploy`, the Dokploy half of the knowledge base. Read when the preflight hits a Dokploy 404/502 it cannot explain, or when attaching a domain end to end.

## Reaching the host

- When the Dokploy host refuses SSH and exposes no docker API port (2375/2376), go through the hypervisor. If the Dokploy server is a VM or LXC on a host you can reach, drive docker through it: `ssh pve "pct exec 300 -- docker ps"`. In this infra, Dokploy is LXC CT 300 on the `pve` host (see `~/.ssh/config`).
- The **Traefik API on port 8080 is the source of truth for routing**: `GET http://<dokploy-host>:8080/api/http/routers` and `/api/http/services`. The service URL shows `http://<appName>:<runtimePort>`; its `serverStatus` only means "config loaded", never "backend reachable". A router with `entryPoints: ["web"]` and `tls: null` is a domain saved with HTTPS off.
- `application.readAppMonitoring` (MCP) returning CPU/memory rows proves the container is running even while routing is broken — use it to separate "app is down" from "ingress is down".
- The MCP has **no deployment log endpoint**, but it does have `domain.create`/`domain.update`. Prefer the dashboard for a first attach: a domain created via MCP arrives with `certificateType: none` and no HTTPS router until you pass `https: true` and `certificateType: letsencrypt` yourself. Read state with `domain.byApplicationId`, `overview.domains`, `application_one`.

## The 404/502 ladder

Read the symptom on the Traefik host or via a `Host:` header against its LAN address, then act:

| Symptom | Meaning | Next step |
|---|---|---|
| 404 on both 80 and 443 | no router for that Host | attach a domain in the dashboard |
| 404 on 443 only | domain attached with HTTPS off | enable HTTPS on the domain (arms Let's Encrypt) |
| 502 | router matches, backend unreachable | compare the domain's port field to the container's runtime `PORT` |
| 502 with correct port | DNS name answers to an orphaned VIP, or a nested-LXC host whose IPVS never worked | VIP recovery below |
| `000` from the public internet | router port-forward or firewall missing | forward 80 + 443 to the Dokploy host; 80 is the ACME challenge |

## Finding the runtime port

Dokploy overrides the Dockerfile's `ENV PORT` at runtime — the app listens on its assignment regardless of `EXPOSE`. Read it from:
1. the Traefik service URL (`:8080/api/http/services` → `http://<appName>:<port>`), or
2. `docker exec <container> env | grep ^PORT` on the host, or
3. the container startup log ("…listening on http://0.0.0.0:<port>").

Set the domain's port field to that number — never to the Dockerfile's.

## Orphaned VIP recovery

Use when the backend is healthy (container `Up`, `node -e fetch …` inside returns 200, monitoring shows data) but Traefik still answers 502 and `docker exec dokploy-traefik wget http://<appName>:<port>` connects to an IP that is **not** in `docker network inspect dokploy-network`.

What happened: the app runs as a Docker service whose DNS name resolves to a virtual IP backed by an IPVS route. Removing the task container by hand deletes that route, but the service object keeps the VIP — every later deploy lands on a fresh container IP that the dead VIP never forwards to.

**On a Dokploy host that is itself an LXC container (or any nested-container setup), the default VIP mode can be broken from day one, not just after a `docker rm -f`.** The swarm VIP needs the kernel's `ip_vs` module working inside the container's network namespace, and a nested LXC does not provide it: `/proc/net/ip_vs` is empty in every namespace, the DNS name resolves to the VIP, and every connection is refused — while `docker network inspect` shows the container healthy on a completely different IP. A Dokploy app in this shape 502s from its first deploy no matter how many times you redeploy. `docker service update --force` does not help: it converges, hands out a fresh container IP, and the VIP still routes nowhere. Diagnose by comparing the DNS answer from inside the traefik container (`docker exec dokploy-traefik getent hosts <appName>`) against the container list in `docker network inspect dokploy-network` — a DNS IP that no container holds is the signature. The standing fix is `docker service update --endpoint-mode dnsrr <appName>` on every deploy (the name then resolves straight to the task container IP, with no VIP in the path), which also clears the stale-record case below.

Recovery, in order:
1. `docker service rm <appName>` on the host, then redeploy (MCP `application_deploy` or dashboard). The new service gets a new VIP and DNS follows it.
2. If `rm` + redeploy is not possible, or DNS still returns the stale record, or the host is a nested LXC where VIP mode never worked: `docker service update --endpoint-mode dnsrr <appName>` — the name then resolves straight to the task container IP, with no VIP in the path. Dokploy recreates the service on every deploy, so **dnsrr must be re-applied after each redeploy**; treat it as part of the deploy sequence on an LXC host, not a one-time fix. Restart the traefik container afterwards so its resolver drops the stale record.
3. Verify the whole path: a fresh container on `dokploy-network` reaches `http://<appName>:<port>`; then the domain answers through the Traefik `Host:` header; then from the public IP once DNS and port-forward land.

## Attaching a domain, end to end

1. Dashboard → project → application → Domains → add: host, **port = the container's runtime PORT**, HTTPS on, Let's Encrypt.
2. DNS: A record to a public IP that `validateDomain` accepts — its error lists them, and the host's LAN address is never among them. Cloudflare: **DNS only** (grey cloud).
3. Router: forward **80 + 443** to the Dokploy host — 80 is the ACME challenge, 443 is traffic. No public 80, no certificate.
4. Exercise the routing before DNS lands: `curl -k -H "Host: <domain>" https://<dokploy-lan-ip>/`.
5. Throwaway test domain when you must prove routing without touching managed DNS: `<anything>.<public-ip>.sslip.io` resolves immediately and `validateDomain` accepts the public IP.
