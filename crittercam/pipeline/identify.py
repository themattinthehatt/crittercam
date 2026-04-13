"""Phase 5 identification: compute embeddings and assign individual identities.

Two-phase processing per run:
  1. Embedding — process pending embedding jobs, write .npy files, update
     detections with embedding_path and reid model provenance.
  2. Matching — for each embedded-but-unassigned detection, compare against
     the per-species gallery of known individuals using cosine similarity and
     assign or create an individual row.
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from crittercam.identifier.base import Identifier
from crittercam.pipeline.db import mark_job, now

logger = logging.getLogger(__name__)


@dataclass
class IdentifySummary:
    """Summary of an identify run.

    Attributes:
        embedded: number of detections successfully embedded
        identified: number of detections assigned to an individual
        individuals: number of distinct individuals present in the batch
        errors: mapping of filename to error message for failed embeddings
    """

    embedded: int = 0
    identified: int = 0
    individuals: int = 0
    errors: dict[str, str] = field(default_factory=dict)


def enqueue_pending(
    conn: sqlite3.Connection,
    species: list[str] | None = None,
) -> int:
    """Scan for active detections without embedding jobs and insert pending jobs.

    Finds active detections that have a crop (required for embedding) but no
    existing processing_jobs row for job_type='embedding'. Inserts a pending
    job for each. Idempotent: detections with any existing embedding job
    (pending, running, done, or error) are skipped.

    Args:
        conn: open database connection
        species: leaf names to restrict to (e.g. ['felis catus']), or None
            for all species

    Returns:
        number of new jobs created
    """
    species_filter = _build_species_filter(species)
    conditions = [
        'd.is_active = 1',
        'd.crop_path IS NOT NULL',
        "NOT EXISTS ("
        "  SELECT 1 FROM processing_jobs pj"
        "  WHERE pj.detection_id = d.id AND pj.job_type = 'embedding'"
        ")",
    ]
    if species_filter['clause']:
        conditions.append(species_filter['clause'])

    where = ' AND '.join(conditions)
    rows = conn.execute(
        f'SELECT d.id FROM detections d WHERE {where}',
        species_filter['params'],
    ).fetchall()

    if not rows:
        return 0

    conn.executemany(
        "INSERT INTO processing_jobs (detection_id, job_type, status)"
        " VALUES (:detection_id, 'embedding', 'pending')",
        [{'detection_id': row['id']} for row in rows],
    )
    conn.commit()
    return len(rows)


def reidentify_all(
    conn: sqlite3.Connection,
    species: list[str] | None = None,
) -> int:
    """Clear algorithm-assigned identity and embedding fields; reset embedding jobs.

    Algorithm-assigned detections and unmatched detections (embedding written
    but no individual yet) have their embedding and identity fields cleared.
    Human-assigned detections are left untouched. Individuals whose only
    remaining detections are not human-assigned are deleted. Embedding jobs
    are then reset to pending so they will be reprocessed.

    See Decision 023 for the model-upgrade policy this implements.

    Args:
        conn: open database connection
        species: leaf names to restrict to, or None to clear all species

    Returns:
        number of embedding jobs reset to pending
    """
    species_filter = _build_species_filter(species, table_alias='')

    # clear embedding + identity fields for non-human-assigned active detections
    det_conditions = [
        'is_active = 1',
        "(individual_assigned_by = 'algorithm' OR individual_assigned_by IS NULL)",
    ]
    if species_filter['clause']:
        det_conditions.append(species_filter['clause'])
    det_where = ' AND '.join(det_conditions)
    conn.execute(
        f'''
        UPDATE detections
        SET embedding_path         = NULL,
            reid_model_name        = NULL,
            reid_model_version     = NULL,
            individual_id          = NULL,
            individual_similarity  = NULL,
            individual_assigned_by = NULL,
            individual_assigned_at = NULL
        WHERE {det_where}
        ''',
        species_filter['params'],
    )

    # delete individuals with no remaining human-assigned detections;
    # scope to species if a filter was given
    ind_conditions = [
        'id NOT IN ('
        '  SELECT DISTINCT individual_id FROM detections'
        "  WHERE individual_assigned_by = 'human' AND individual_id IS NOT NULL"
        ')',
    ]
    ind_params: dict = {}
    if species_filter['clause']:
        ind_leaf_conditions = []
        for i, leaf in enumerate(species or []):
            ind_params[f'ind_leaf{i}'] = leaf
            ind_leaf_conditions.append(f'species_leaf = :ind_leaf{i}')
        ind_conditions.append(f'({" OR ".join(ind_leaf_conditions)})')
    ind_where = ' AND '.join(ind_conditions)
    conn.execute(f'DELETE FROM individuals WHERE {ind_where}', ind_params)
    conn.commit()

    # reset embedding jobs to pending; join to detections for species filter
    if species_filter['clause']:
        job_params = dict(species_filter['params'])
        det_id_where = f'SELECT id FROM detections WHERE {species_filter["clause"]}'
        cursor = conn.execute(
            f'''
            UPDATE processing_jobs
            SET status = 'pending', started_at = NULL,
                completed_at = NULL, error_msg = NULL
            WHERE job_type = 'embedding'
              AND status != 'pending'
              AND detection_id IN ({det_id_where})
            ''',
            job_params,
        )
    else:
        cursor = conn.execute(
            "UPDATE processing_jobs"
            " SET status = 'pending', started_at = NULL,"
            "     completed_at = NULL, error_msg = NULL"
            " WHERE job_type = 'embedding' AND status != 'pending'"
        )
    conn.commit()
    return cursor.rowcount


def reset_assignments(
    conn: sqlite3.Connection,
    species: list[str] | None = None,
) -> int:
    """Clear algorithm-assigned individual identities without touching embeddings.

    Unlike reidentify_all, this leaves embedding_path, reid_model_name, and
    reid_model_version intact so Phase 1 does not need to re-run. Use this
    before match_pending when exploring threshold values.

    Human-assigned detections are left untouched. Orphaned individuals (those
    with no remaining human-assigned detections) are deleted so the gallery
    starts clean for the next match_pending call.

    Args:
        conn: open database connection
        species: leaf names to restrict to, or None for all species

    Returns:
        number of detections cleared
    """
    species_filter = _build_species_filter(species, table_alias='')

    assignment_conditions = [
        'is_active = 1',
        "individual_assigned_by = 'algorithm'",
    ]
    if species_filter['clause']:
        assignment_conditions.append(species_filter['clause'])
    assignment_where = ' AND '.join(assignment_conditions)
    cursor = conn.execute(
        f'''
        UPDATE detections
        SET individual_id          = NULL,
            individual_similarity  = NULL,
            individual_assigned_by = NULL,
            individual_assigned_at = NULL
        WHERE {assignment_where}
        ''',
        species_filter['params'],
    )
    n_cleared = cursor.rowcount

    # delete orphaned individuals so the gallery is clean for re-matching;
    # scope to species when a filter is given
    ind_conditions = [
        'id NOT IN ('
        '  SELECT DISTINCT individual_id FROM detections'
        "  WHERE individual_assigned_by = 'human' AND individual_id IS NOT NULL"
        ')',
    ]
    ind_params: dict = {}
    if species_filter['clause']:
        ind_leaf_conditions = []
        for i, leaf in enumerate(species or []):
            ind_params[f'ind_leaf{i}'] = leaf
            ind_leaf_conditions.append(f'species_leaf = :ind_leaf{i}')
        ind_conditions.append(f'({" OR ".join(ind_leaf_conditions)})')
    conn.execute(
        f'DELETE FROM individuals WHERE {" AND ".join(ind_conditions)}',
        ind_params,
    )
    conn.commit()
    return n_cleared


def match_pending(
    data_root: Path,
    conn: sqlite3.Connection,
    threshold: float = 0.5,
    species: list[str] | None = None,
) -> IdentifySummary:
    """Run gallery-based individual matching for embedded-but-unassigned detections.

    For each active detection that has an embedding but no individual assignment,
    compares against the per-species gallery using vectorized cosine similarity.
    A detection whose nearest neighbour exceeds the threshold is assigned to that
    individual; one below threshold creates a new individual row.

    Intended to be called after reset_assignments when exploring threshold values,
    or internally by identify_pending after embedding completes.

    Args:
        data_root: root directory for resolving embedding file paths
        conn: open database connection
        threshold: minimum cosine similarity to match an existing individual
        species: leaf names to restrict to, or None for all species

    Returns:
        IdentifySummary with identified count (embedded is always 0)
    """
    summary = IdentifySummary()
    assigned_individuals: set[int] = set()
    species_filter = _build_species_filter(species)

    unmatched = conn.execute(
        f'''
        SELECT d.id, d.embedding_path, d.label
        FROM detections d
        WHERE d.is_active = 1
          AND d.embedding_path IS NOT NULL
          AND d.individual_id IS NULL
        {('AND ' + species_filter['clause']) if species_filter['clause'] else ''}
        ORDER BY d.id
        ''',
        species_filter['params'],
    ).fetchall()

    if not unmatched:
        return summary

    # group by species leaf to build one gallery matrix per species
    species_to_dets: dict[str, list] = {}
    for det in unmatched:
        leaf = det['label'].split(';')[-1]
        species_to_dets.setdefault(leaf, []).append(det)

    # pre-load per-species gallery matrices with zero padding for new entries
    galleries: dict[str, dict] = {}
    for leaf, dets in species_to_dets.items():
        db_gallery = _get_gallery(conn, data_root, leaf)
        n_existing = len(db_gallery)
        n_new_max = len(dets)

        embed_dim: int | None = None
        if db_gallery:
            embed_dim = db_gallery[0][1].shape[0]
        else:
            for det in dets:
                emb_path = data_root / det['embedding_path']
                if emb_path.exists():
                    embed_dim = np.load(emb_path).shape[0]
                    break

        if embed_dim is None:
            logger.warning(f'cannot determine embedding dimension for {leaf!r}; skipping')
            continue

        capacity = n_existing + n_new_max
        matrix = np.zeros((capacity, embed_dim), dtype=np.float32)
        individual_ids: list[int | None] = [None] * capacity
        for i, (ind_id, vec) in enumerate(db_gallery):
            matrix[i] = vec
            individual_ids[i] = ind_id

        galleries[leaf] = {
            'matrix': matrix,
            'individual_ids': individual_ids,
            'n_filled': n_existing,
        }

    for det in unmatched:
        detection_id = det['id']
        species_leaf = det['label'].split(';')[-1]
        g = galleries.get(species_leaf)

        if g is None:
            continue

        emb_abs = data_root / det['embedding_path']
        if not emb_abs.exists():
            logger.warning(
                f'embedding file missing for detection {detection_id}: {emb_abs}'
            )
            continue

        query_vector = np.load(emb_abs).astype(np.float32)
        ts = now()

        n_filled = g['n_filled']
        if n_filled > 0:
            sims = g['matrix'][:n_filled] @ query_vector
            best_idx = int(np.argmax(sims))
            best_sim = float(sims[best_idx])
            best_individual_id = g['individual_ids'][best_idx]
        else:
            best_individual_id, best_sim = None, -1.0

        if best_individual_id is not None and best_sim >= threshold:
            individual_id = best_individual_id
            similarity = best_sim
            logger.info(
                f'detection {detection_id}: matched individual {individual_id}'
                f' ({species_leaf}, similarity={similarity:.3f})'
            )
        else:
            individual_id = _next_individual_id(conn)
            conn.execute(
                '''
                INSERT INTO individuals (id, species_leaf, created_at, updated_at)
                VALUES (:id, :species_leaf, :created_at, :updated_at)
                ''',
                {'id': individual_id, 'species_leaf': species_leaf, 'created_at': ts, 'updated_at': ts},
            )
            conn.commit()
            similarity = 1.0
            logger.info(
                f'detection {detection_id}: new individual {individual_id}'
                f' ({species_leaf})'
            )

        conn.execute(
            '''
            UPDATE detections
            SET individual_id          = :individual_id,
                individual_similarity  = :individual_similarity,
                individual_assigned_by = 'algorithm',
                individual_assigned_at = :individual_assigned_at
            WHERE id = :detection_id
            ''',
            {
                'individual_id': individual_id,
                'individual_similarity': similarity,
                'individual_assigned_at': ts,
                'detection_id': detection_id,
            },
        )
        conn.commit()

        g['matrix'][n_filled] = query_vector
        g['individual_ids'][n_filled] = individual_id
        g['n_filled'] += 1

        assigned_individuals.add(individual_id)
        summary.identified += 1

    summary.individuals = len(assigned_individuals)
    return summary


def identify_pending(
    data_root: Path,
    conn: sqlite3.Connection,
    identifier: Identifier,
    threshold: float = 0.5,
    species: list[str] | None = None,
) -> IdentifySummary:
    """Run embedding generation and gallery-based identity matching.

    Phase 1 processes pending embedding jobs: runs the identifier on each
    detection crop, saves the resulting vector as a .npy file alongside the
    crop in derived/, and updates the detection row with embedding_path and
    reid model provenance.

    Phase 2 matches embedded-but-unassigned detections against the per-species
    gallery of known individuals using cosine similarity. A detection above
    threshold is assigned to the nearest individual; one below threshold
    creates a new individual row with individual_similarity = 1.0 as a
    sentinel (founding detection, no match was made).

    Idempotent: jobs already in done/error state are not reprocessed unless
    reset first via reset_errors() or reidentify_all().

    Args:
        data_root: root directory for the image archive and derived assets
        conn: open database connection
        identifier: identifier implementing the Identifier protocol
        threshold: minimum cosine similarity to assign an existing individual;
            detections below this score create a new individual
        species: leaf names to restrict to, or None for all species

    Returns:
        IdentifySummary with counts and per-file error details
    """
    summary = IdentifySummary()

    # --- Phase 1: embedding ---

    species_filter = _build_species_filter(species)
    pending = conn.execute(
        f'''
        SELECT pj.id AS job_id, pj.detection_id,
               d.crop_path, d.label,
               i.filename
        FROM processing_jobs pj
        JOIN detections d ON d.id = pj.detection_id
        JOIN images i ON i.id = d.image_id
        WHERE pj.job_type = 'embedding' AND pj.status = 'pending'
        {('AND ' + species_filter['clause']) if species_filter['clause'] else ''}
        ORDER BY pj.id
        ''',
        species_filter['params'],
    ).fetchall()

    for job in pending:
        job_id = job['job_id']
        detection_id = job['detection_id']
        filename = job['filename']
        crop_path_rel = job['crop_path']

        if not crop_path_rel:
            # guard: enqueue_pending filters these, but be defensive
            mark_job(conn, job_id, 'done', completed_at=now())
            conn.commit()
            continue

        crop_abs = data_root / crop_path_rel
        mark_job(conn, job_id, status='running', started_at=now())
        conn.commit()

        try:
            embedding = identifier.embed(crop_abs)
        except Exception as exc:
            msg = str(exc)
            logger.error(f'embedding failed on {filename}: {msg}')
            mark_job(conn, job_id, 'error', completed_at=now(), error_msg=msg)
            conn.commit()
            summary.errors[filename] = msg
            continue

        crop_rel_path = Path(crop_path_rel)
        emb_rel = crop_rel_path.parent / f'{crop_rel_path.stem}_emb.npy'
        emb_abs = data_root / emb_rel
        emb_abs.parent.mkdir(parents=True, exist_ok=True)
        np.save(emb_abs, embedding.vector)

        ts = now()
        conn.execute(
            '''
            UPDATE detections
            SET embedding_path     = :embedding_path,
                reid_model_name    = :reid_model_name,
                reid_model_version = :reid_model_version
            WHERE id = :detection_id
            ''',
            {
                'embedding_path': str(emb_rel),
                'reid_model_name': identifier.model_name,
                'reid_model_version': identifier.model_version,
                'detection_id': detection_id,
            },
        )
        mark_job(conn, job_id, 'done', completed_at=ts)
        conn.commit()

        summary.embedded += 1
        label_leaf = job['label'].split(';')[-1]
        logger.info(f'embedded {filename} ({label_leaf}, detection {detection_id})')

    # --- Phase 2: gallery matching ---

    match_summary = match_pending(data_root, conn, threshold, species)
    summary.identified = match_summary.identified
    summary.individuals = match_summary.individuals
    return summary


def _build_species_filter(
    species: list[str] | None,
    table_alias: str = 'd',
) -> dict:
    """Build a SQL WHERE clause fragment and params dict for species leaf filtering.

    Args:
        species: list of species leaf names, or None for no filter
        table_alias: table alias prefix for the label column (e.g. 'd' produces
            'd.label'); pass an empty string for unaliased contexts such as
            UPDATE statements

    Returns:
        dict with 'clause' (a bare condition string, no leading AND) and
        'params' (dict of named bind parameters)
    """
    if not species:
        return {'clause': '', 'params': {}}

    col = f'{table_alias}.label' if table_alias else 'label'
    params: dict = {}
    leaf_conditions = []
    for i, leaf in enumerate(species):
        params[f'labellike{i}'] = f'%;{leaf}'
        leaf_conditions.append(f'{col} LIKE :labellike{i}')

    return {'clause': f'({" OR ".join(leaf_conditions)})', 'params': params}


def name_individual(
    conn: sqlite3.Connection,
    individual_id: int,
    nickname: str,
) -> None:
    """Set or update the nickname for an individual.

    Args:
        conn: open database connection
        individual_id: id of the individual to name
        nickname: display name to assign

    Raises:
        ValueError: if the individual_id does not exist
    """
    row = conn.execute(
        'SELECT id FROM individuals WHERE id = :id', {'id': individual_id},
    ).fetchone()
    if row is None:
        raise ValueError(f'individual id not found: {individual_id}')

    conn.execute(
        'UPDATE individuals SET nickname = :nickname, updated_at = :ts WHERE id = :id',
        {'nickname': nickname, 'ts': now(), 'id': individual_id},
    )
    conn.commit()


def merge_individuals(
    conn: sqlite3.Connection,
    ids: list[int],
) -> int:
    """Merge a set of individuals into the one with the lowest id.

    All detections belonging to any of the given individuals are reassigned to
    the lowest id in the list and marked as human-assigned with individual_similarity
    cleared. The individual rows for the non-target ids are deleted and the
    target individual's updated_at is refreshed.

    Args:
        conn: open database connection
        ids: individual ids to merge; must contain at least two entries and all
            must exist in the individuals table

    Returns:
        the target individual id (the lowest in ids)

    Raises:
        ValueError: if fewer than two ids are provided or any id does not exist
    """
    if len(ids) < 2:
        raise ValueError(f'merge requires at least two individual ids; got {len(ids)}')

    placeholders = ', '.join(f':id{i}' for i in range(len(ids)))
    id_params = {f'id{i}': v for i, v in enumerate(ids)}

    found = {
        row['id']
        for row in conn.execute(
            f'SELECT id FROM individuals WHERE id IN ({placeholders})', id_params,
        ).fetchall()
    }
    missing = sorted(set(ids) - found)
    if missing:
        raise ValueError(f'individual id(s) not found: {missing}')

    target = min(ids)
    ts = now()

    conn.execute(
        f'''
        UPDATE detections
        SET individual_id          = :target,
            individual_assigned_by = 'human',
            individual_assigned_at = :ts,
            individual_similarity  = NULL
        WHERE individual_id IN ({placeholders})
        ''',
        {**id_params, 'target': target, 'ts': ts},
    )

    others = [v for v in ids if v != target]
    other_placeholders = ', '.join(f':del{i}' for i in range(len(others)))
    other_params = {f'del{i}': v for i, v in enumerate(others)}
    conn.execute(
        f'DELETE FROM individuals WHERE id IN ({other_placeholders})',
        other_params,
    )

    conn.execute(
        'UPDATE individuals SET updated_at = :ts WHERE id = :target',
        {'ts': ts, 'target': target},
    )

    conn.commit()
    return target


def _next_individual_id(conn: sqlite3.Connection) -> int:
    """Return the smallest positive integer not currently used as an individual id.

    SQLite's INTEGER PRIMARY KEY never reuses a deleted rowid (it picks
    max-ever + 1), so after deleting a batch of individuals the auto-assigned
    ids would continue from the old high-water mark. Explicitly choosing the
    lowest available id keeps numbering compact after a reset.

    Args:
        conn: open database connection

    Returns:
        smallest integer >= 1 not present in the individuals table
    """
    row = conn.execute(
        '''
        SELECT COALESCE(MIN(gap), 1) FROM (
            SELECT 1 AS gap
            WHERE NOT EXISTS (SELECT 1 FROM individuals WHERE id = 1)
            UNION ALL
            SELECT id + 1 FROM individuals
            WHERE NOT EXISTS (SELECT 1 FROM individuals b WHERE b.id = individuals.id + 1)
        )
        '''
    ).fetchone()[0]
    return row


def _get_gallery(
    conn: sqlite3.Connection,
    data_root: Path,
    species_leaf: str,
) -> list[tuple[int, np.ndarray]]:
    """Load the gallery of known individuals for a species.

    Queries all active detections of the given species that have been assigned
    an individual and have an embedding on disk.

    Args:
        conn: open database connection
        data_root: root directory for resolving embedding file paths
        species_leaf: leaf segment of the taxonomy label (e.g. 'felis catus')

    Returns:
        list of (individual_id, unit-normalised float32 embedding vector)
    """
    rows = conn.execute(
        '''
        SELECT individual_id, embedding_path
        FROM detections
        WHERE is_active = 1
          AND individual_id IS NOT NULL
          AND embedding_path IS NOT NULL
          AND label LIKE :labellike
        ''',
        {'labellike': f'%;{species_leaf}'},
    ).fetchall()

    gallery = []
    for row in rows:
        emb_path = data_root / row['embedding_path']
        if emb_path.exists():
            gallery.append((row['individual_id'], np.load(emb_path).astype(np.float32)))
        else:
            logger.warning(f'gallery embedding missing: {emb_path}')
    return gallery
