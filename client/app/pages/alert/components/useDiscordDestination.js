import { useEffect, useState } from "react";

import AlertSubscription from "@/services/alert-subscription";

export default function useDiscordDestination(alertId, refreshToken = 0) {
  const [hasDiscordWebhook, setHasDiscordWebhook] = useState(false);
  const [destinationOptions, setDestinationOptions] = useState({});

  useEffect(() => {
    if (!alertId) {
      setHasDiscordWebhook(false);
      setDestinationOptions({});
      return undefined;
    }

    let cancelled = false;

    AlertSubscription.query({ alertId }).then(subs => {
      if (cancelled) {
        return;
      }
      const discordSub = (subs || []).find(sub => sub.destination?.type === "discord_webhook");
      setHasDiscordWebhook(!!discordSub);
      setDestinationOptions(discordSub?.destination?.options || {});
    });

    return () => {
      cancelled = true;
    };
  }, [alertId, refreshToken]);

  return { hasDiscordWebhook, destinationOptions };
}
