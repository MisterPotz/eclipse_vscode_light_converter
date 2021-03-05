package ru.bmstu.rk9.rao.ui.simulation;

import org.eclipse.core.commands.AbstractHandler;
import org.eclipse.core.commands.ExecutionEvent;
import org.eclipse.core.commands.ExecutionException;
import org.eclipse.ui.handlers.HandlerUtil;
import org.eclipse.ui.handlers.RadioState;

import ru.bmstu.rk9.rao.ui.simulation.SimulationSynchronizer.ExecutionMode;

public class SetSimulationModeHandler extends AbstractHandler {
	@Override
	public Object execute(ExecutionEvent event) throws ExecutionException {
		if (HandlerUtil.matchesRadioState(event))
			return null;

		String executionMode = event.getParameter(RadioState.PARAMETER_ID);

		HandlerUtil.updateRadioState(event.getCommand(), executionMode);

		SimulationModeDispatcher.setMode(ExecutionMode.getByString(executionMode));

		return null;
	}
}
