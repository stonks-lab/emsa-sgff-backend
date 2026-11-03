import logging
from fastapi import APIRouter, Query, Response
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/metros", tags=["metros"])


@router.get("/pai/versiones")
def get_pai_versiones(response: Response):
    response.headers["Cache-Control"] = "no-store"
    from app.data.sql_server import query_df_bi, _normalize_col
    df = query_df_bi("SELECT * FROM dbo.PAI_Proyectos")
    df.columns = [_normalize_col(c) for c in df.columns]
    logger.info("[versiones] columnas: %s", list(df.columns))

    ano_col = next((c for c in df.columns if c in ('ano_pai', 'año_pai', 'anio_pai')), None)
    ver_col = next((c for c in df.columns if 'version' in c), None)
    logger.info("[versiones] ano_col=%s ver_col=%s", ano_col, ver_col)

    if not ano_col or not ver_col:
        logger.warning("[versiones] No se encontraron columnas ano/version. Columnas: %s", list(df.columns))
        return []

    df = df[[ano_col, ver_col]].dropna(subset=[ano_col]).drop_duplicates()

    latest: dict = df.groupby(ano_col)[ver_col].max().to_dict()
    result = []
    for _, row in df.iterrows():
        try:
            ano   = int(float(row[ano_col]))
            ver_f = float(row[ver_col])
            ver_s = str(int(ver_f)) if ver_f == int(ver_f) else f"{ver_f}"
            es_ultima = ver_f == float(latest[row[ano_col]])
            result.append({
                "key":      f"{ano}|{ver_s}",
                "label":    f"PAI {ano} — v{ver_s}{'  ★' if es_ultima else ''}",
                "ano":      ano,
                "version":  ver_s,
                "es_ultima": es_ultima,
            })
        except Exception as e:
            logger.debug("[versiones] fila saltada: %s", e)
    logger.info("[versiones] total versiones: %d", len(result))
    return result


@router.get("/pai")
def get_pai(ano: Optional[int] = Query(None), version: Optional[str] = Query(None)):
    import pandas as pd
    from app.data.sql_server import query_df_bi, _normalize_col, _keep_latest_pai

    df = query_df_bi("SELECT * FROM dbo.PAI_Proyectos")
    df.columns = [_normalize_col(c) for c in df.columns]

    ano_col = next((c for c in df.columns if c in ('ano_pai', 'año_pai', 'anio_pai')), None)
    ver_col = next((c for c in df.columns if 'version' in c.lower()), None)

    if ano and ano_col:
        df = df[pd.to_numeric(df[ano_col], errors='coerce') == ano].copy()

    if version and ver_col:
        try:
            ver_f = float(version)
            df = df[pd.to_numeric(df[ver_col], errors='coerce') == ver_f].copy()
        except ValueError:
            pass
    else:
        df = _keep_latest_pai(df)

    if 'mes' in df.columns:
        parsed = pd.to_datetime(df['mes'], format='%Y-%m-%d', errors='coerce')
        df['mes'] = parsed.dt.strftime('%Y-%m').where(parsed.notna(), '')
    for col in [c for c in df.columns if 'metro' in c]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df.fillna('').to_dict('records')


@router.get("/avance")
def get_avance():
    from app.data.sql_server import get_avance_semanal
    return get_avance_semanal()


@router.get("/presupuesto-anos")
def get_presupuesto_anos():
    from app.data.sql_server import query_df_bi, _normalize_col
    df = query_df_bi("SELECT * FROM dbo.PAI_Proyectos")
    df.columns = [_normalize_col(c) for c in df.columns]
    ano_col = next((c for c in df.columns if c in ('ano_pai', 'año_pai', 'anio_pai')), None)
    logger.info("[presupuesto-anos] columnas: %s  ano_col=%s", list(df.columns), ano_col)
    if not ano_col:
        logger.warning("[presupuesto-anos] No se encontró columna de año. Columnas: %s", list(df.columns))
        return {"anos": []}
    anos = sorted(
        list({int(float(v)) for v in df[ano_col].dropna().tolist() if str(v).replace('.', '', 1).isdigit()}),
        reverse=True,
    )
    logger.info("[presupuesto-anos] años encontrados: %s", anos)
    return {"anos": anos}


@router.get("/presupuesto-perforacion")
def get_presupuesto_perforacion(ano: Optional[int] = Query(None)):
    import pandas as pd
    from app.data.sql_server import query_df_bi, query_df, _normalize_col, _keep_latest_pai

    # ── PAI metros ───────────────────────────────────────────────────────────
    df = query_df_bi("SELECT * FROM dbo.PAI_Proyectos")
    df.columns = [_normalize_col(c) for c in df.columns]

    ano_col = next((c for c in df.columns if c in ('ano_pai', 'año_pai', 'anio_pai')), None)
    if ano and ano_col:
        df = df[pd.to_numeric(df[ano_col], errors='coerce') == ano].copy()
    df = _keep_latest_pai(df)

    id_col    = 'id_blanco' if 'id_blanco' in df.columns else 'projectcode'
    metro_col = next((c for c in df.columns if c == 'metros_pai'),
                     next((c for c in df.columns if 'metro' in c.lower() and 'pai' in c.lower()), None))
    if not metro_col:
        metro_col = next((c for c in df.columns if 'metro' in c.lower()), None)
    if not metro_col:
        return {"proyectos": [], "totales": {}}

    df[metro_col] = pd.to_numeric(df[metro_col], errors='coerce').fillna(0)

    nombre_col = next((c for c in df.columns if 'nombre' in c), None)
    nombres: dict = {}
    try:
        df_dim = query_df(
            "SELECT [ID_BLANCO], [NOM_RESUMEN_ID_BLANCO] FROM dbo.dim_Proyectos "
            "WHERE [ID_BLANCO] IS NOT NULL AND [NOM_RESUMEN_ID_BLANCO] IS NOT NULL"
        )
        df_dim['ID_BLANCO'] = df_dim['ID_BLANCO'].astype(str).str.strip()
        nombres = df_dim.set_index('ID_BLANCO')['NOM_RESUMEN_ID_BLANCO'].to_dict()
        logger.warning("[ppto-perf] dim_Proyectos nombres cargados: %d", len(nombres))
    except Exception as e:
        logger.warning("[presupuesto-perforacion] no se pudo cargar dim_Proyectos: %s", e)

    def _tipo_sondaje(t: str) -> str:
        t = str(t).upper()
        return 'AR' if ('AR' in t and 'DDH' not in t) else 'DHH'

    df['_tipo'] = df['tipo_sondaje'].fillna('').apply(_tipo_sondaje)
    df['_proy'] = df[id_col].fillna('').astype(str).str.strip()

    grp_pai = df.groupby(['_proy', '_tipo'])[metro_col].sum().reset_index()
    grp_pai.columns = ['proyecto', 'tipo', 'metros']

    # Fallback: nombre desde PAI si dim no lo tiene
    if nombre_col:
        for proy, row in df.drop_duplicates('_proy').set_index('_proy').iterrows():
            if proy not in nombres and row[nombre_col]:
                nombres[proy] = str(row[nombre_col])

    pivot = grp_pai.pivot(index='proyecto', columns='tipo', values='metros').fillna(0).reset_index()

    # ── Costos desde Proyecciones_P&C ────────────────────────────────────────
    # costos[proyecto][tipo] = {ppt_usd, usd_por_metro}
    costos: dict = {}
    try:
        df_pyc = query_df(
            "SELECT [ID_BLANCO], [CODIGO PROVEEDOR], [UN], [CTD], "
            "[PRECIO UNITARIO (US$)], [_version_presupuesto] "
            "FROM dbo.[Proyecciones_P&C] WHERE UN IN ('m / AR', 'm / DDH')"
        )
        logger.warning("[ppto-perf] pyc total filas UN AR/DDH: %d", len(df_pyc))

        if not df_pyc.empty:
            df_pyc['_ctd']    = pd.to_numeric(df_pyc['CTD'],                  errors='coerce').fillna(0)
            df_pyc['_precio'] = pd.to_numeric(df_pyc['PRECIO UNITARIO (US$)'], errors='coerce').fillna(0)
            df_pyc['_ppto']   = df_pyc['_ctd'] * df_pyc['_precio']

            # Mantener solo la versión más reciente por (blanco, contrato)
            # Mantener solo filas con CTD > 0 y, entre versiones duplicadas
            # (mismo proyecto+contrato+descripción), quedarse con la de mayor versión
            df_pyc = df_pyc[df_pyc['_ctd'] > 0].copy()
            df_pyc['_ver_n'] = pd.to_numeric(
                df_pyc['_version_presupuesto'].str.extract(r'^(\d+)', expand=False),
                errors='coerce'
            ).fillna(0)
            # Por (proyecto, contrato, UN) conservar la versión más alta
            df_pyc = df_pyc.sort_values('_ver_n', ascending=False)
            df_pyc = df_pyc.drop_duplicates(
                subset=['ID_BLANCO', 'CODIGO PROVEEDOR', 'UN'], keep='first'
            )
            logger.warning("[ppto-perf] pyc tras filtro CTD>0 + dedup: %d", len(df_pyc))

            # Tipo sale directo del UN: 'm / AR' → AR, 'm / DDH' → DHH
            df_pyc['_tipo'] = df_pyc['UN'].apply(
                lambda u: 'AR' if 'AR' in str(u).upper() else 'DHH'
            )
            logger.warning("[ppto-perf] tipos encontrados: %s", df_pyc['_tipo'].value_counts().to_dict())

            df_pyc = df_pyc[df_pyc['_tipo'].notna()].copy()
            df_pyc['_proy'] = df_pyc['ID_BLANCO'].fillna('').astype(str).str.strip()
            logger.warning("[ppto-perf] filas con tipo clasificado: %d, ctd>0: %d",
                len(df_pyc), int((df_pyc['_ctd'] > 0).sum()))

            for (proy, tipo), g in df_pyc.groupby(['_proy', '_tipo']):
                ppt = float(g['_ppto'].sum())
                ctd = float(g['_ctd'].sum())
                upm = round(ppt / ctd, 2) if ctd > 0 else None
                costos.setdefault(proy, {})[tipo] = {'ppt_usd': ppt, 'usd_por_metro': upm}

        logger.warning("[ppto-perf] costos P&C calculados para %d proyectos", len(costos))

    except Exception as e:
        logger.warning("[presupuesto-perforacion] error costos P&C: %s", e, exc_info=True)

    # ── Fallback: EP para proyectos sin costo en P&C ─────────────────────────
    try:
        import re
        from app.data.loader import load_ep

        ep_all = load_ep()
        # Filtrar rango CLP/USD (700-1500); excluye contratos en UF (~39.000)
        fx_valid = ep_all[(ep_all['ExchageRate'] > 700) & (ep_all['ExchageRate'] < 1500)]['ExchageRate']
        fx = float(fx_valid.mean()) if len(fx_valid) > 0 else 950.0

        METER_UNITS = {'mts', 'm', 'metros', 'metro', 'MTS', 'Metros'}

        def _tipo_ep(item_desc: str, ctt_desc: str) -> str | None:
            for text in (item_desc, ctt_desc):
                t = str(text).upper()
                if 'DDH' in t or 'DIAMANT' in t or 'SUBTERR' in t:
                    return 'DHH'
                if 'AIRE REVERSO' in t or bool(re.search(r'\bAR\b', t)):
                    return 'AR'
                if 'DRENAJE' in t or 'POZO PROD' in t:
                    return 'AR'
            return None

        ep_perf = ep_all[
            ep_all['Tipo_contrato'].str.contains('Perforaci', case=False, na=False)
        ].copy()

        if ano and 'AÑO' in ep_perf.columns:
            ep_perf = ep_perf[pd.to_numeric(ep_perf['AÑO'], errors='coerce') == ano].copy()

        ep_perf['_tipo'] = ep_perf.apply(
            lambda r: _tipo_ep(r.get('item_descripcion', ''), r.get('Descripcion_ctt', '')), axis=1
        )
        # Normalizar cod_blanco: pad sufijo numérico de 1 dígito a 2 (CAMPANE2 → CAMPANE02)
        ep_perf['_proy'] = (
            ep_perf['cod_blanco'].fillna('').astype(str).str.strip()
            .apply(lambda c: re.sub(r'(?<=[A-Za-z])(\d)$', lambda m: m.group(1).zfill(2), c))
        )

        # Fallback de tipo: si el PAI solo tiene un tipo para ese proyecto, usarlo
        pai_tipos_por_proy: dict = (
            grp_pai.groupby('proyecto')['tipo'].apply(set).to_dict()
        )
        def _tipo_por_pai(proy: str, tipo_ep_val) -> str | None:
            if pd.notna(tipo_ep_val):
                return tipo_ep_val
            tipos_pai = pai_tipos_por_proy.get(proy, set())
            return next(iter(tipos_pai)) if len(tipos_pai) == 1 else None

        ep_perf['_tipo'] = ep_perf.apply(
            lambda r: _tipo_por_pai(r['_proy'], r['_tipo']), axis=1
        )
        ep_perf = ep_perf[ep_perf['_tipo'].notna()].copy()
        ep_perf['_monto'] = pd.to_numeric(ep_perf['monto_consumido'], errors='coerce').fillna(0)

        # Metros: solo ítems con unidad de longitud
        ep_perf['_es_metro'] = ep_perf['unidad'].isin(METER_UNITS)
        ep_perf['_ctd_m']    = pd.to_numeric(ep_perf['cantidad_consumida'], errors='coerce').fillna(0)
        ep_perf['_ctd_m']    = ep_perf['_ctd_m'].where(ep_perf['_es_metro'], 0)

        ep_added = 0
        for (proy, tipo), g in ep_perf.groupby(['_proy', '_tipo']):
            if costos.get(proy, {}).get(tipo):
                continue
            # Costo total del contrato (todos los ítems) como numerador
            ppt_usd = round(float(g['_monto'].sum()) / fx, 2)
            # Metros solo de ítems con unidad lineal como denominador
            ctd = float(g['_ctd_m'].sum())
            upm = round(ppt_usd / ctd, 2) if ctd > 0 else None
            costos.setdefault(proy, {})[tipo] = {'ppt_usd': ppt_usd, 'usd_por_metro': upm}
            ep_added += 1

        logger.warning("[ppto-perf] costos EP fallback añadidos: %d (fx=%.0f)", ep_added, fx)

    except Exception as e:
        logger.warning("[presupuesto-perforacion] error costos EP: %s", e, exc_info=True)

    # ── Build response ───────────────────────────────────────────────────────
    proyectos = []
    for _, row in pivot.iterrows():
        proy = str(row['proyecto'])
        ar   = float(row.get('AR',  0))
        dhh  = float(row.get('DHH', 0))
        c_ar  = costos.get(proy, {}).get('AR',  {})
        c_dhh = costos.get(proy, {}).get('DHH', {})
        proyectos.append({
            "proyecto":          proy,
            "nombre":            str(nombres.get(proy, '')),
            "metros_ar":         ar  if ar  > 0 else None,
            "metros_dhh":        dhh if dhh > 0 else None,
            "ppt_usd_ar":        c_ar.get('ppt_usd'),
            "ppt_usd_dhh":       c_dhh.get('ppt_usd'),
            "usd_por_metro_ar":  c_ar.get('usd_por_metro'),
            "usd_por_metro_dhh": c_dhh.get('usd_por_metro'),
        })

    tot_ar  = float(grp_pai[grp_pai['tipo'] == 'AR']['metros'].sum())
    tot_dhh = float(grp_pai[grp_pai['tipo'] == 'DHH']['metros'].sum())

    tot_ppt_ar  = sum(p['ppt_usd_ar']  or 0 for p in proyectos)
    tot_ppt_dhh = sum(p['ppt_usd_dhh'] or 0 for p in proyectos)

    ar_pairs  = [(p['ppt_usd_ar'],  p['metros_ar'])  for p in proyectos if p['ppt_usd_ar']  and p['metros_ar']]
    dhh_pairs = [(p['ppt_usd_dhh'], p['metros_dhh']) for p in proyectos if p['ppt_usd_dhh'] and p['metros_dhh']]
    tot_upm_ar  = round(sum(p for p, _ in ar_pairs)  / sum(m for _, m in ar_pairs),  2) if ar_pairs  else None
    tot_upm_dhh = round(sum(p for p, _ in dhh_pairs) / sum(m for _, m in dhh_pairs), 2) if dhh_pairs else None

    return {
        "proyectos": proyectos,
        "totales": {
            "metros_ar":         tot_ar,
            "metros_dhh":        tot_dhh,
            "ppt_usd_ar":        tot_ppt_ar  if tot_ppt_ar  > 0 else None,
            "ppt_usd_dhh":       tot_ppt_dhh if tot_ppt_dhh > 0 else None,
            "usd_por_metro_ar":  tot_upm_ar,
            "usd_por_metro_dhh": tot_upm_dhh,
        },
    }


@router.get("/curva-s")
def get_curva_s(
    tipo: str            = Query('all'),
    ano:  Optional[int]  = Query(None),
):
    import pandas as pd
    from datetime import datetime
    from app.data.sql_server import query_df_bi, _normalize_col, _keep_latest_pai

    # ── PAI ──────────────────────────────────────────────────────────────────
    df = query_df_bi("SELECT * FROM dbo.PAI_Proyectos")
    df.columns = [_normalize_col(c) for c in df.columns]

    ano_col = next((c for c in df.columns if c in ('ano_pai', 'año_pai', 'anio_pai')), None)
    if ano and ano_col:
        df = df[pd.to_numeric(df[ano_col], errors='coerce') == ano].copy()
    df = _keep_latest_pai(df)

    def _tipo_fn(t: str) -> str:
        t = str(t).upper()
        return 'AR' if ('AR' in t and 'DDH' not in t) else 'DHH'

    tipo_up = tipo.upper()
    if tipo_up in ('AR', 'DHH'):
        df['_tipo'] = df['tipo_sondaje'].fillna('').apply(_tipo_fn)
        df = df[df['_tipo'] == tipo_up].copy()

    if 'mes' not in df.columns:
        return _empty_curva()
    parsed = pd.to_datetime(df['mes'], format='%Y-%m-%d', errors='coerce')
    df['_mes'] = parsed.dt.strftime('%Y-%m').where(parsed.notna(), None)
    df = df[df['_mes'].notna()].copy()

    metro_pai = next((c for c in df.columns if c == 'metros_pai'),
                     next((c for c in df.columns if 'metro' in c and 'pai' in c), None))
    if not metro_pai:
        return _empty_curva()

    df[metro_pai] = pd.to_numeric(df[metro_pai], errors='coerce').fillna(0)
    pai_mes = df.groupby('_mes')[metro_pai].sum().sort_index()
    all_meses = list(pai_mes.index)
    if not all_meses:
        return _empty_curva()

    # ── Avance real ──────────────────────────────────────────────────────────
    av_por_mes: dict[str, float] = {}
    try:
        av_raw = query_df_bi("SELECT * FROM dbo.Avance_Semanal")
        av_raw.columns = [_normalize_col(c) for c in av_raw.columns]
        fecha_col = next((c for c in av_raw.columns if 'fecha' in c and c != 'fecha_carga'), None)
        # Preferir metros_avance sobre metros_avance_real (más completo)
        _av_pref = ['metros_avance', 'metros_avance_real']
        met_av = next(
            (c for c in _av_pref if c in av_raw.columns),
            next((c for c in av_raw.columns if 'metro' in c and ('avance' in c or 'real' in c)), None),
        )
        if fecha_col and met_av:
            if tipo_up in ('AR', 'DHH') and 'tipo_sondaje' in av_raw.columns:
                av_raw['_tipo'] = av_raw['tipo_sondaje'].fillna('').apply(_tipo_fn)
                av_raw = av_raw[av_raw['_tipo'] == tipo_up].copy()
            av_raw['_mes'] = pd.to_datetime(av_raw[fecha_col], errors='coerce').dt.strftime('%Y-%m')
            av_raw[met_av] = pd.to_numeric(av_raw[met_av], errors='coerce').fillna(0)
            av_por_mes = av_raw.groupby('_mes')[met_av].sum().to_dict()
    except Exception:
        pass

    # ── P&C total presupuestado (USD) ─────────────────────────────────────────
    total_ppt_usd = 0.0
    try:
        from app.data.sql_server import query_df as _qdf
        un_filter = {'AR': "'m / AR'", 'DHH': "'m / DDH'"}.get(tipo_up, "'m / AR','m / DDH'")
        df_pyc = _qdf(
            f"SELECT [ID_BLANCO],[CODIGO PROVEEDOR],[UN],[CTD],[PRECIO UNITARIO (US$)],"
            f"[_version_presupuesto] FROM dbo.[Proyecciones_P&C] WHERE UN IN ({un_filter})"
        )
        if not df_pyc.empty:
            df_pyc['_ctd']    = pd.to_numeric(df_pyc['CTD'],                   errors='coerce').fillna(0)
            df_pyc['_precio'] = pd.to_numeric(df_pyc['PRECIO UNITARIO (US$)'], errors='coerce').fillna(0)
            df_pyc = df_pyc[df_pyc['_ctd'] > 0].copy()
            df_pyc['_ver_n'] = pd.to_numeric(
                df_pyc['_version_presupuesto'].str.extract(r'^(\d+)', expand=False), errors='coerce'
            ).fillna(0)
            df_pyc = df_pyc.sort_values('_ver_n', ascending=False).drop_duplicates(
                subset=['ID_BLANCO', 'CODIGO PROVEEDOR', 'UN'], keep='first'
            )
            total_ppt_usd = float((df_pyc['_ctd'] * df_pyc['_precio']).sum())
    except Exception:
        pass

    # ── EP financiero por mes (USD) ───────────────────────────────────────────
    ep_por_mes_usd: dict[str, float] = {}
    tiene_ep = False
    total_ep_usd = 0.0
    avg_ep_rate  = 0.0
    last_ep_month: str | None = None
    try:
        import re
        from app.data.loader import load_ep as _load_ep
        ep_all = _load_ep()
        fx_v = ep_all[(ep_all['ExchageRate'] > 700) & (ep_all['ExchageRate'] < 1500)]['ExchageRate']
        fx   = float(fx_v.mean()) if len(fx_v) > 0 else 950.0

        ep_p = ep_all[ep_all['Tipo_contrato'].str.contains('Perforaci', case=False, na=False)].copy()

        if tipo_up in ('AR', 'DHH'):
            def _tep(item_desc: str, ctt_desc: str) -> str | None:
                for t in (str(item_desc).upper(), str(ctt_desc).upper()):
                    if 'DDH' in t or 'DIAMANT' in t or 'SUBTERR' in t: return 'DHH'
                    if 'AIRE REVERSO' in t or bool(re.search(r'\bAR\b', t)): return 'AR'
                    if 'DRENAJE' in t or 'POZO PROD' in t: return 'AR'
                return None
            ep_p['_tipo'] = ep_p.apply(
                lambda r: _tep(r.get('item_descripcion', ''), r.get('Descripcion_ctt', '')), axis=1
            )
            ep_p = ep_p[ep_p['_tipo'] == tipo_up].copy()

        if ano and 'AÑO' in ep_p.columns:
            ep_p = ep_p[pd.to_numeric(ep_p['AÑO'], errors='coerce') == ano].copy()

        if 'Fecha_Periodo' in ep_p.columns:
            ep_p['_mes_ep']    = ep_p['Fecha_Periodo'].dt.strftime('%Y-%m')
            ep_p['_monto_usd'] = pd.to_numeric(ep_p['monto_consumido'], errors='coerce').fillna(0) / fx
            ep_por_mes_usd     = ep_p.groupby('_mes_ep')['_monto_usd'].sum().to_dict()
            total_ep_usd       = sum(ep_por_mes_usd.values())
            tiene_ep           = total_ep_usd > 0
            if tiene_ep:
                recent = sorted(m for m, v in ep_por_mes_usd.items() if v > 0)[-3:]
                avg_ep_rate  = sum(ep_por_mes_usd[m] for m in recent) / len(recent) if recent else 0.0
                last_ep_month = max((m for m in ep_por_mes_usd if ep_por_mes_usd[m] > 0), default=None)
    except Exception:
        pass

    tiene_avance = bool(av_por_mes)
    now_mes      = datetime.now().strftime('%Y-%m')
    total_pai    = float(pai_mes.sum())

    # ── Build S-curve ────────────────────────────────────────────────────────
    data    = []
    cum_pai = 0.0
    cum_av  = 0.0
    cum_ep  = 0.0

    for mes in all_meses:
        cum_pai += float(pai_mes.get(mes, 0))
        es_futuro = mes > now_mes

        # Physical avance
        if tiene_avance and not es_futuro:
            cum_av += float(av_por_mes.get(mes, 0))
            cum_av_val: float | None = cum_av
        else:
            cum_av_val = None

        # Financial plan: distribute P&C budget proportionally to PAI progress
        cum_ppt_usd = round(total_ppt_usd * cum_pai / total_pai, 2) if total_pai and total_ppt_usd else 0

        # Financial actual (EP)
        if tiene_ep and not es_futuro:
            cum_ep += float(ep_por_mes_usd.get(mes, 0))
            cum_ep_val: float | None = cum_ep if cum_ep > 0 else None
        else:
            cum_ep_val = None

        # EP projection (future months past last EP)
        cum_ep_proy: float | None = None
        if tiene_ep and es_futuro and last_ep_month and mes > last_ep_month and avg_ep_rate > 0:
            months_ahead = sum(1 for m in all_meses if last_ep_month < m <= mes)
            cum_ep_proy = round(cum_ep + avg_ep_rate * months_ahead, 2)

        pct_pai = round(cum_pai / total_pai * 100, 2) if total_pai else None
        pct_av  = round(cum_av / total_pai * 100, 2)  if (total_pai and cum_av_val is not None) else None

        data.append({
            "mes":              mes,
            "pct_ppt_fin":      None,
            "pct_pai_fis":      pct_pai,
            "pct_av_fis":       pct_av,
            "pct_ep_fin":       None,
            "pct_av_fis_proy":  None,
            "pct_ep_fin_proy":  None,
            "cum_ppt_usd":      cum_ppt_usd,
            "cum_pai_metros":   round(cum_pai, 1),
            "cum_av_metros":    round(cum_av_val, 1) if cum_av_val is not None else None,
            "cum_ep_usd":       round(cum_ep_val, 2) if cum_ep_val is not None else None,
            "cum_av_metros_proy": None,
            "cum_ep_usd_proy":    round(cum_ep_proy, 2) if cum_ep_proy is not None else None,
            "es_futuro":        es_futuro,
        })

    last_av = max((m for m, v in av_por_mes.items() if v > 0), default=None) if av_por_mes else None

    return {
        "data":            data,
        "totales":         {
            "ppt_usd":    round(total_ppt_usd, 2),
            "pai_metros": round(total_pai, 1),
            "av_metros":  round(cum_av, 1),
            "ep_usd":     round(total_ep_usd, 2),
        },
        "tiene_ep":        tiene_ep,
        "tiene_avance":    tiene_avance,
        "avg_av_rate":     0,
        "avg_ep_rate":     round(avg_ep_rate, 2),
        "last_ep_month":   last_ep_month or last_av,
        "ep_bridge_month": None,
    }


def _empty_curva() -> dict:
    return {
        "data": [], "totales": {"ppt_usd": 0, "pai_metros": 0, "av_metros": 0, "ep_usd": 0},
        "tiene_ep": False, "tiene_avance": False,
        "avg_av_rate": 0, "avg_ep_rate": 0, "last_ep_month": None, "ep_bridge_month": None,
    }


@router.get("/pyc-debug")
def get_pyc_debug():
    import math
    from fastapi.responses import JSONResponse
    from app.data.sql_server import query_df

    def _safe(obj):
        if isinstance(obj, float) and math.isnan(obj):
            return None
        if isinstance(obj, dict):
            return {k: _safe(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_safe(v) for v in obj]
        return obj

    result: dict = {}

    try:
        df_dim = query_df("SELECT TOP 10 [ID_CUADRA],[ID_PROYECTO],[NOMBRE],[ID_BLANCO] FROM dbo.dim_Proyectos")
        result["dim_proy_sample"] = df_dim.where(df_dim.notna(), None).to_dict("records")
        result["dim_id_proyecto_sample"] = df_dim['ID_PROYECTO'].dropna().astype(str).head(10).tolist()
        result["dim_id_blanco_sample"]   = df_dim['ID_BLANCO'].dropna().astype(str).head(10).tolist()
    except Exception as e:
        result["dim_proy_error"] = str(e)

    try:
        import pandas as pd
        from app.data.sql_server import query_df_bi, _normalize_col
        df_pai = query_df_bi("SELECT * FROM dbo.PAI_Proyectos")
        df_pai.columns = [_normalize_col(c) for c in df_pai.columns]
        result["pai_columnas"] = list(df_pai.columns)
        id_col = 'id_blanco' if 'id_blanco' in df_pai.columns else df_pai.columns[0]
        result["pai_id_col_usado"] = id_col
        non_null = df_pai[id_col].dropna()
        non_null = non_null[non_null.astype(str).str.strip() != '']
        result["pai_sample_ids"] = non_null.astype(str).head(15).tolist()
        result["pai_total_non_null_ids"] = int(len(non_null))

        # Cross-check: how many PAI ids match dim_Proyectos ID_BLANCO
        if not df_pai.empty and "dim_id_blanco_sample" in result:
            df_dim_all = query_df("SELECT [ID_BLANCO],[NOMBRE] FROM dbo.dim_Proyectos WHERE [ID_BLANCO] IS NOT NULL")
            dim_ids = set(df_dim_all['ID_BLANCO'].astype(str).str.strip().tolist())
            pai_ids = set(non_null.astype(str).str.strip().tolist())
            matched = pai_ids & dim_ids
            result["join_matches_count"] = len(matched)
            result["join_matches_sample"] = list(matched)[:10]
            result["pai_ids_no_match_sample"] = list(pai_ids - dim_ids)[:10]
    except Exception as e:
        result["pai_sample_error"] = str(e)

    return JSONResponse(content=_safe(result))


@router.get("/pai/debug")
def get_pai_debug():
    from app.data.sql_server import query_df_bi
    import pandas as pd

    df = query_df_bi("SELECT * FROM dbo.PAI_Proyectos")
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    info: dict = {"total_filas": len(df), "columnas": list(df.columns)}
    for key in df.columns:
        if any(w in key for w in ('version', 'fecha_carga', 'ano', 'año', 'anio')):
            try:
                unicos = sorted(df[key].dropna().astype(str).unique().tolist())
                info[f"valores_{key}"] = unicos[:30]
            except Exception:
                pass
    metro_cols = [c for c in df.columns if 'metro' in c]
    info["columnas_metros"] = metro_cols
    for mc in metro_cols:
        df[mc] = pd.to_numeric(df[mc], errors='coerce').fillna(0)
        info[f"suma_{mc}"] = round(float(df[mc].sum()), 1)
    return info
