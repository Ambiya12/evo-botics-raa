import { useEffect, useState } from "react";
import { Video } from "lucide-react";
import { Panel } from "../ui/Panel";
import { getVideoStreamUrl } from "../../services/robotVideoService";

export function VideoFeedPanel() {
  const [streamUrl, setStreamUrl] = useState<string | null>(
    getVideoStreamUrl(),
  );

  useEffect(() => {
    const id = setInterval(() => {
      setStreamUrl(getVideoStreamUrl());
    }, 2000);
    return () => clearInterval(id);
  }, []);

  return (
    <Panel
      eyebrow="Camera"
      title="RGB Feed"
      action={<Video size={20} strokeWidth={1.8} />}
      className="video-feed"
    >
      {streamUrl === null ? (
        <div className="video-feed__placeholder">
          <Video size={40} strokeWidth={1.5} />
          <p>Video feed — connect robot to enable</p>
        </div>
      ) : (
        <img
          src={streamUrl}
          alt="Robot camera feed"
          className="video-feed__img"
        />
      )}
    </Panel>
  );
}
