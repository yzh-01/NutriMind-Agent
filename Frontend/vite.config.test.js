import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import { resolveApiTarget } from './vite.config'

const temporaryDirectories = []

async function createEnvironment(contents = '') {
  const directory = await mkdtemp(path.join(tmpdir(), 'nutrimind-vite-'))
  temporaryDirectories.push(directory)
  if (contents) await writeFile(path.join(directory, '.env.development'), contents, 'utf8')
  return directory
}

afterEach(async () => {
  await Promise.all(temporaryDirectories.splice(0).map((directory) => rm(directory, { recursive: true, force: true })))
})

describe('Vite API proxy target', () => {
  it('loads VITE_API_TARGET from the active mode environment file', async () => {
    const directory = await createEnvironment('VITE_API_TARGET=http://127.0.0.1:8123\n')

    expect(resolveApiTarget('development', directory)).toBe('http://127.0.0.1:8123')
  })

  it('falls back to the documented local backend address', async () => {
    const directory = await createEnvironment()

    expect(resolveApiTarget('development', directory)).toBe('http://localhost:9999')
  })
})
