declare module "adm-zip" {
  type ZipEntry = {
    entryName: string;
    isDirectory: boolean;
    getData(): Buffer;
  };

  export default class AdmZip {
    constructor(buffer: Buffer);
    getEntries(): ZipEntry[];
  }
}
