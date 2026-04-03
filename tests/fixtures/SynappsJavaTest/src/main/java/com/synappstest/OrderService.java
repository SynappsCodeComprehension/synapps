package com.synappstest;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.client.RestTemplate;

public class OrderService {

    @Autowired
    private OrderRepository orderRepository;

    @Autowired
    private RestTemplate restTemplate;

    public Animal createAnimal(String name) {
        Animal animal = new Cat();
        return orderRepository.save(animal);
    }

    public long countAnimals() {
        return orderRepository.count();
    }

    public Animal getAnimalFromService(String url) {
        return restTemplate.getForObject(url, Animal.class);
    }
}
