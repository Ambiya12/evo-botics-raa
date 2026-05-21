let streamUrl: string | null = null;

export function setVideoStreamUrl(url: string | null): void {
  streamUrl = url;
}

export function getVideoStreamUrl(): string | null {
  return streamUrl;
}
