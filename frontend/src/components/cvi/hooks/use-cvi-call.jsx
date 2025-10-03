import { useCallback } from 'react';
import { useDaily } from '@daily-co/daily-react';

export const useCVICall = () => {
	const daily = useDaily();

	const joinCall = useCallback(
		({ url }) => {
			daily?.join({
				url: url,
				inputSettings: {
					audio: {
						processor: {
							type: 'noise-cancellation',
						},
					},
				},
			});
		},
		[daily]
	);

	const leaveCall = useCallback(() => {
		daily?.leave();
	}, [daily]);

	return { joinCall, leaveCall };
};
