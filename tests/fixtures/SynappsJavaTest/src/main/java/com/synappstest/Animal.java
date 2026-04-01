package com.synappstest;

/**
 * Base class for all animals.
 * Used to verify Javadoc does not break INHERITS/IMPLEMENTS resolution.
 */
public abstract class Animal implements IAnimal {
    private final String name;

    public Animal(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }

    @Override
    public abstract String speak();

    @Override
    public void move() {
        System.out.println(getName() + " is moving");
    }
}
