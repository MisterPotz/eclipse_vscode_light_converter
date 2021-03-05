package ru.bmstu.rk9.rao.lib.logger;

import java.util.LinkedList;
import java.util.Queue;

import ru.bmstu.rk9.rao.lib.notification.Notifier;

public class Logger {
	public final void log(Object object) {
		messages.add(object.toString());
		notifyChange(NotificationCategory.NEW_LOG_ENTRY);
	}

	Queue<String> messages = new LinkedList<>();

	public final String poll() {
		return messages.poll();
	}

	public enum NotificationCategory {
		NEW_LOG_ENTRY
	};

	private final Notifier<NotificationCategory> notifier = new Notifier<NotificationCategory>(
			NotificationCategory.class);

	public final Notifier<NotificationCategory> getNotifier() {
		return notifier;
	}

	private final void notifyChange(final NotificationCategory category) {
		notifier.notifySubscribers(category);
	}
}
