package ru.bmstu.rk9.rao.lib.type;

public class RangedInteger {
	private int lo;
	private int hi;

	public RangedInteger(int lo, int hi) {
		this.lo = lo;
		this.hi = hi;
	}

	private int value;

	public void set(int value) throws Exception {
		if (value > hi || value < lo)
			throw new Exception("Out of bounds");

		this.value = value;
	}

	public int get() {
		return value;
	}
}
