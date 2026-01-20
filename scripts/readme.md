## Fix `hnswlib` Issue

## What’s going on (1 minute)

* `hnswlib` is a **compiled** Python package (`.so` file).
* If it’s compiled on a CPU with newer instruction support, then running it later on an older CPU can crash (SIGILL).
* The fix is to compile it **in a CPU-generic way** (`-march=x86-64 -mtune=generic`) and then **reuse that same compiled wheel everywhere**.

That’s why we build a “portable wheel” once and then just install it repeatedly.

---

## Where/when to run each script

### Script A: `build_portable_wheels.sh`

**Run it once** in an environment that:

1. has a compiler toolchain available (`g++`, `make`, etc.), and
2. can download the hnswlib source (from your allowed pip indexes), and
3. uses the same Python/venv you’ll run with (your `/venv/bin/python`).

On Pegasus, the safest way is:

✅ **Run it inside a SLURM interactive job on a compute node** (same way you ran debugpy), inside the same container.

Example flow:

1. Request an interactive job (like you already do with `scripts/slurm_pty.sh ...`)
2. Inside that job, inside the container:

   ```bash
   cd /home/abuali/projects/KBExtraction
   bash scripts/build_portable_wheels.sh
   ```

This produces a wheel file in `./.wheelhouse/`.

Why compute node? Because that environment is closest to where your job will run and has the right architecture/permissions.

**Is it one-time?**
➡️ Yes, *as long as* you don’t change Python version / hnswlib version / compiler environment.
If you upgrade Python (e.g., 3.10 → 3.11) or want a different hnswlib version, rebuild once again.

---

### Script B: `install_from_wheelhouse.sh`

**Run it at the start of every job** (or at least every time you start a fresh container/venv).

Because:

* a job might land on a node where your venv is “clean” or missing that package
* reinstalling from your local wheelhouse is fast and deterministic

So you typically do:

* add this in your job startup (`debug.sh`, `train.sh`, etc.):

  ```bash
  bash scripts/install_from_wheelhouse.sh
  ```

Then run your actual program.

---

## A very practical “do this” recipe

### One-time setup (first time only)

Inside an interactive SLURM job + container:

```bash
cd /home/abuali/projects/KBExtraction
bash scripts/build_portable_wheels.sh
```

You should now have something like:
`/home/abuali/projects/KBExtraction/.wheelhouse/hnswlib-...whl`

### Every time you run on any node

At the beginning of your `debug.sh` (or right before starting python):

```bash
bash scripts/install_from_wheelhouse.sh
```

That’s it.

---

## What “where building works” *really* meant

Sometimes building fails because of one of these:

* missing `g++` / `python3-dev` headers
* pip can’t fetch build requirements (common on HPC with restricted indexes)
* build isolation tries to download stuff you can’t access

So “where building works” = “a node/container where the compile + pip install succeeds”.

Since you already successfully built once: you’ve found such a place.

---

## Tiny improvement I strongly recommend

Make `.wheelhouse` live on a shared filesystem you always see from any node (your project dir probably is). If you ever run from a different working directory, set:

```bash
export WHEELHOUSE=/home/abuali/projects/KBExtraction/.wheelhouse
```

---

If you paste the output of:

```bash
ls -lh .wheelhouse
python -c "import sys; print(sys.version)"
```

I can tell you if your current wheelhouse is correctly set up and version-safe.
