package com.synappstest;

/**
 * Concrete animal that extends Animal.
 * Verifies INHERITS edge with Javadoc-shifted line numbers.
 */
public class Dog extends Animal {
    public Dog(String name) {
        super(name);
    }

    @Override
    public String speak() {
        return "Woof!";
    }

    /**
     * Fetch an item and announce it.
     * @param item the item to fetch
     */
    public void fetch(String item) {
        speak();
        Formatter.format(item);
    }
}
