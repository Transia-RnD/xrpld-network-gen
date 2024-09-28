import { it, expect } from 'vitest'
import { createStandaloneBinary, createStandaloneImage } from '../../src/main'
import { isFolderAndFiles } from '../utils'
import path from 'node:path'

const basedir = path.join(__dirname, '..', '..')

it('standalone image', async () => {
  await createStandaloneImage(
    'trace',
    'ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501',
    'ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501',
    'xrpl',
    1,
    'rippleci',
    '2.0.0-b4',
  )
  const folder = `${basedir}/xrpl-2.0.0-b4`
  const files = [
    'Dockerfile',
    'docker-compose.yml',
    'start.sh',
    'entrypoint',
    'genesis.json',
    'stop.sh',
  ]
  const { folderExists, filesExist } = isFolderAndFiles(folder, files)
  expect(folderExists).toBe(true)
  expect(filesExist).toEqual(files.map(() => true))
})

it('standalone binary', async () => {
  await createStandaloneBinary(
    'trace',
    'ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501',
    'ED87E0EA91AAFFA130B78B75D2CC3E53202AA1BD8AB3D5E7BAC530C8440E328501',
    'xahau',
    21337,
    'https://build.xahau.tech',
    '2024.1.25-release+738',
  )
  const folder = `${basedir}/xahau-2024.1.25-release+738`
  const files = [
    'Dockerfile',
    'docker-compose.yml',
    'start.sh',
    'entrypoint',
    'genesis.json',
    'stop.sh',
  ]
  const { folderExists, filesExist } = isFolderAndFiles(folder, files)
  expect(folderExists).toBe(true)
  expect(filesExist).toEqual(files.map(() => true))
})
